"""Exploratory lens diagnostic (docs/plans/round4-lens-diagnostic.md), GPU.

Part 1 reads the jacobian-lens library's example prompts; Parts 2 and 3 read stored
residuals of 12 agents at `system_end` and P2. Each readout is done with the J-lens and with
the plain logit lens (no J map), top-25 printable tokens at the 10 plan layers.
"""

import json
from pathlib import Path

import pandas as pd
import torch
from safetensors.torch import load_file

from colx import provenance, qwen
from colx.extract.recompute import block_outputs
from colx.extract.stored import read_shard_rows
from colx.jlens.diagnostic_words import (
    EXPECTED,
    example_verdicts,
    expected_hit,
    instruction_verdicts,
    matched_words,
    own_words,
    relative_logits,
)
from colx.jlens.lens import LAYERS, load_maps, readout
from colx.jlens.reference import _reference_library
from colx.jlens.render import printable_mask, top_tokens
from colx.unembed import from_model

RUNS = (
    "deception__audit_01__collusion",
    "deception__audit_02__collusion",
    "deception__cyber_01__collusion",
)
LENSES = ("jlens", "logit")


class Reader:
    """Lens logits and top-25 printable tokens, for the J-lens or the plain logit lens."""

    def __init__(self, model, tokenizer, lens_path: Path) -> None:
        self.unembed = from_model(model)
        self.maps = {k: v.to(model.device) for k, v in load_maps(lens_path).items()}
        self.mask = printable_mask(tokenizer, self.unembed.lm_head.shape[0])
        self.decode = lambda i: tokenizer.decode([int(i)])

    def logits(self, resid: torch.Tensor, layer: int, lens: str) -> torch.Tensor:
        """Lens logits of residuals [n, d] at one layer."""
        if lens == "jlens":
            return readout(resid, self.maps[layer], self.unembed)
        return self.unembed(resid)

    def tokens(self, logits: torch.Tensor) -> list[list[str]]:
        """Top-25 printable tokens per row."""
        return [[self.decode(i) for i in row] for row in top_tokens(logits, self.mask).cpu()]


def examples_part(model, tokenizer, reader: Reader) -> pd.DataFrame:
    """Part 1: does an expected token appear at the last token of each library example?"""
    library_examples, resolve_prompt = _library_examples()
    examples = {e.slug: e for e in library_examples}
    rows = []
    for slug, expected in EXPECTED.items():
        ids = tokenizer(resolve_prompt(examples[slug], tokenizer))["input_ids"]
        resid = block_outputs(model, ids, [len(ids) - 1])[0]  # [blocks, d]
        for lens in LENSES:
            for layer in LAYERS:
                tokens = reader.tokens(reader.logits(resid[layer : layer + 1], layer, lens))[0]
                rows.append(
                    {"part": 1, "item": slug, "lens": lens, "layer": layer,
                     "tokens": tokens, "hit": expected_hit(tokens, expected)}
                )  # fmt: skip
    return pd.DataFrame(rows)


def _library_examples():
    """The pinned library's example prompts (imported read-only from its folder)."""
    _reference_library()
    from jlens.examples import EXAMPLES, resolve_prompt

    return EXAMPLES, resolve_prompt


def _agent_rows(out_dir: Path) -> pd.DataFrame:
    """The 12 diagnostic agents with their own words and a chance word list."""
    agents = pd.read_parquet(out_dir / "agents.parquet")
    briefs = pd.read_parquet(out_dir / "runs.parquet").set_index("run_id")["brief"]
    picked = agents[agents["run_id"].isin(RUNS)].sort_values(["run_id", "agent_index"])
    picked = picked.reset_index(drop=True)
    picked["own"] = [
        own_words(s, briefs[r]) for s, r in zip(picked.system_prompt, picked.run_id, strict=True)
    ]
    picked["chance_words"] = [picked["own"][(i + 4) % len(picked)] for i in range(len(picked))]
    return picked


def _stored_system_end(extract_dir: Path, agents: pd.DataFrame) -> torch.Tensor:
    """Stored residuals at `system_end` of the agents' final calls: [n, blocks, d]."""
    index = pd.read_parquet(extract_dir / "samples.parquet")
    finals = index[index["phase"] == "final"].set_index(["run_id", "agent"])["sample_idx"]
    out = []
    for run_id, group in agents.groupby("run_id", sort=True):
        rows = [int(finals[(run_id, a)]) for a in group["agent"]]
        out.append(
            read_shard_rows(
                extract_dir / "shards" / f"{run_id}.safetensors", rows, ("system_end",)
            )[:, 0]
        )
    return torch.cat(out)


def _word_rows(
    agents: pd.DataFrame, position: str, lens: str, layer: int, tokens: list
) -> list[dict]:
    """Rows of own-word hits and chance hits per agent for one readout."""
    rows = []
    for a, t in zip(agents.itertuples(), tokens, strict=True):
        rows.append(
            {
                "part": 2 if position == "system_end" else 3,
                "item": f"{a.run_id}|{a.agent}",
                "role": a.role,
                "position": position,
                "lens": lens,
                "layer": layer,
                "tokens": t,
                "hits": sorted(matched_words(t, a.own)),
                "chance": sorted(matched_words(t, a.chance_words)),
            }
        )
    return rows


def instruction_parts(extract_dir: Path, out_dir: Path, reader: Reader) -> pd.DataFrame:
    """Parts 2 and 3: own instruction words at system_end, and at P2 plain vs relative."""
    agents = _agent_rows(out_dir)
    index = pd.read_parquet(out_dir / "activations_index.parquet")
    p2_rows = [
        index.index[(index.run_id == r) & (index.agent == a)][0]
        for r, a in zip(agents.run_id, agents.agent, strict=True)
    ]
    p2 = load_file(str(out_dir / "activations.safetensors"))["resid"][p2_rows, 1]
    sys_end = _stored_system_end(extract_dir, agents)
    rows = []
    for lens in LENSES:
        for layer in LAYERS:
            rows += _word_rows(
                agents,
                "system_end",
                lens,
                layer,
                reader.tokens(reader.logits(sys_end[:, layer], layer, lens)),
            )
            p2_logits = reader.logits(p2[:, layer], layer, lens)
            rows += _word_rows(agents, "P2", lens, layer, reader.tokens(p2_logits))
            relative = torch.cat(
                [relative_logits(p2_logits[i : i + 4]) for i in range(0, len(agents), 4)]
            )
            rows += _word_rows(agents, "P2-relative", lens, layer, reader.tokens(relative))
    return pd.DataFrame(rows)


def run_diagnostic(model_path: str, lens_path: Path, extract_dir: Path, out_dir: Path) -> dict:
    """Run all three parts; save readouts and verdicts under `diagnostic/`, return verdicts."""
    tokenizer, model = qwen.load_tokenizer(model_path), qwen.load_model(model_path)
    reader = Reader(model, tokenizer, lens_path)
    table = pd.concat(
        [examples_part(model, tokenizer, reader), instruction_parts(extract_dir, out_dir, reader)]
    )
    path = out_dir / "diagnostic" / "readouts.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    table.assign(tokens=table["tokens"].map(json.dumps)).to_parquet(path, index=False)
    verdicts = example_verdicts(table) | instruction_verdicts(table)
    meta = provenance.collect("col lens-judge diagnose", label="exploratory", runs=RUNS)
    provenance.write_meta(path, meta)
    (path.parent / "verdicts.json").write_text(
        json.dumps(meta | {"verdicts": verdicts}, indent=2, default=str)
    )
    return verdicts
