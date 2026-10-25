"""Block C of the stego plan (exploratory): the overlap detector on NARCBench-Transfer (Qwen).

Stored extraction (`/workspace/extract/ours-qwen3_32b/qwen3_32b/transfer`): 72 runs (36
collusion, 36 control), 4 agents each, every final call's prompt end (`response_start`,
P1 as on Core) at all 64 blocks. Same lens, 10 layers, renderings and overlap score as
Core (words-relative = relative to the mean over the 288 final calls). No new generation.
Test: overlap run score, collusion vs control, AUROC with scenario bootstrap and shuffles
within scenario.
"""

import json
from pathlib import Path

import pandas as pd
import torch

from colx import provenance, qwen
from colx.analysis.suite import auroc_test
from colx.extract.stored import read_shard_rows
from colx.jlens.filtered import relative_logprobs, word_mask
from colx.jlens.lens import LAYERS, load_maps, readout
from colx.jlens.render import printable_mask, top_tokens
from colx.joint.pairs import overlap_score
from colx.unembed import from_checkpoint


def final_residuals(extract_dir: Path) -> tuple[pd.DataFrame, torch.Tensor]:
    """Final calls (sorted) and their P1 residuals at the 10 layers: [n, 10, d]."""
    s = pd.read_parquet(extract_dir / "samples.parquet")
    calls = s[s.phase == "final"].sort_values(["run_id", "agent"], ignore_index=True)
    blocks = []
    for run_id, g in calls.groupby("run_id", sort=True):
        shard = extract_dir / "shards" / f"{run_id}.safetensors"
        blocks.append(
            read_shard_rows(shard, g.sample_idx.astype(int).tolist(), ("response_start",))[:, 0][
                :, list(LAYERS)
            ]
        )
    return calls[["run_id", "scenario_id", "mode", "agent", "role"]], torch.cat(blocks)


def token_sets(calls: pd.DataFrame, resid: torch.Tensor, model_dir: Path, lens_path: Path) -> dict:
    """Per rendering, {(run_id, agent): set of (layer, token id)} in the top 25."""
    tokenizer, unembed = qwen.load_tokenizer(str(model_dir)), from_checkpoint(model_dir)
    vocab = unembed.lm_head.shape[0]
    masks = {"raw": printable_mask(tokenizer, vocab), "rel": word_mask(tokenizer, vocab)}
    maps, sets = load_maps(lens_path), {"raw": {}, "rel": {}}
    keys = list(zip(calls.run_id, calls.agent, strict=True))
    for li, layer in enumerate(LAYERS):
        logits = readout(resid[:, li], maps[layer], unembed)
        ids = {
            "raw": top_tokens(logits, masks["raw"]),
            "rel": top_tokens(relative_logprobs(logits), masks["rel"]),
        }
        for r, top in ids.items():
            for k, row in zip(keys, top.tolist(), strict=True):
                sets[r].setdefault(k, set()).update((layer, t) for t in row)
    return sets


def run_test(calls: pd.DataFrame, sets: dict, n_boot: int, n_perm: int) -> dict:
    """Overlap score per run and its AUROC, collusion vs control, per rendering."""
    runs = calls.drop_duplicates("run_id").set_index("run_id")
    out = {}
    for r, s in sets.items():
        scores = [
            overlap_score([s[(run, a)] for a in sorted(g.agent)])[0]
            for run, g in calls.groupby("run_id", sort=True)
        ]
        y = (runs.sort_index()["mode"] == "collusion").to_numpy()
        scen = runs.sort_index().scenario_id.to_numpy()
        out[r] = auroc_test(scores, y, scen, scen, n_boot, n_perm)
    return out


def analyse(
    extract_dir: Path, model_dir: Path, lens_path: Path, out_dir: Path, n_boot: int, n_perm: int
) -> dict:
    """Read, score, test; save `transfer_overlap.json` with provenance."""
    calls, resid = final_residuals(extract_dir)
    result = run_test(calls, token_sets(calls, resid, model_dir, lens_path), n_boot, n_perm)
    out_dir.mkdir(parents=True, exist_ok=True)
    record = provenance.collect(
        "col lens-judge transfer overlap",
        label="exploratory",
        result=result,
        runs=int(calls.run_id.nunique()),
    )
    (out_dir / "transfer_overlap.json").write_text(json.dumps(record, indent=1, default=str))
    return result
