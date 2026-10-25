"""Read the Gemma residuals through the converged lens: raw and words-relative top 25.

The same rules as on Qwen (`colx.jlens.render`, `colx.jlens.filtered`):
- raw: the top 25 printable tokens by lens logit;
- words-relative: log-probabilities minus their mean over a group of calls at the same read
  point and layer, then the top 25 word tokens. Groups: all final calls (P1, P2); the
  discussion calls of one round (T-start, T-end).
Outputs follow the Qwen schemas, so the Qwen analysis code runs unchanged:
`final_tokens.parquet` (P1, P2) and `turns_tokens.parquet` (rounds 1-3, T-start, T-end).
"""

from pathlib import Path

import pandas as pd
import torch
from safetensors.torch import load_file

from colx import provenance
from colx.gemma.extract import POINTS
from colx.gemma.model import LAYERS, LENS_SHA256, Unembed, load
from colx.jlens.filtered import word_mask
from colx.jlens.lens import load_maps, sha256_of
from colx.jlens.render import printable_mask
from colx.turns.tokens import layer_ids

READS = {"final": {"P1": "start", "P2": "p2"}, "discussion": {"T-start": "start", "T-end": "end"}}


def point_rows(
    calls: pd.DataFrame,
    resid: torch.Tensor,
    groups: torch.Tensor,
    point: str,
    maps: dict,
    unembed,
    masks: dict,
    layers: tuple[int, ...] = LAYERS,
) -> list[pd.DataFrame]:
    """Long tables of both renderings at one read point, for every plan layer."""
    p = POINTS.index(point)
    frames = []
    for li, layer in enumerate(layers):
        logits = unembed(resid[:, p, li].to(maps[layer].device, torch.float32) @ maps[layer].T)
        for rendering, ids in layer_ids(logits, groups.to(logits.device), masks).items():
            ids = ids.cpu().numpy()
            frame = calls.loc[calls.index.repeat(ids.shape[1])]
            frames.append(
                frame.assign(
                    layer=layer,
                    rendering=rendering,
                    rank=list(range(ids.shape[1])) * len(calls),
                    token_id=ids.reshape(-1),
                )
            )
    return frames


def write_readouts(model_dir: Path, lens_path: Path, out_dir: Path, log=print) -> dict:
    """Check the lens hash, read every call out, save both token tables with provenance."""
    if sha256_of(lens_path) != LENS_SHA256:
        raise ValueError("Gemma lens sha256 does not match the plan")
    calls = pd.read_parquet(out_dir / "calls.parquet")
    resid = load_file(str(out_dir / "resid.safetensors"))["resid"]
    tokenizer, model = load(model_dir)
    unembed, vocab = Unembed(model), model.lm_head.weight.shape[0]
    masks = {"raw": printable_mask(tokenizer, vocab), "rel": word_mask(tokenizer, vocab)}
    maps = {layer: m.to(model.device) for layer, m in load_maps(lens_path, LAYERS).items()}
    texts: dict[int, str] = {}
    out = {}
    for phase, reads in READS.items():
        rows = calls[calls.phase == phase]
        groups = torch.as_tensor(
            rows["round"].to_numpy() if phase == "discussion" else [0] * len(rows)
        )
        sub, frames = resid[rows.index.to_numpy()], []
        keep = rows[["run_id", "agent", "round"]].reset_index(drop=True)
        for position, point in reads.items():
            frames += [
                f.assign(position=position)
                for f in point_rows(keep, sub, groups, point, maps, unembed, masks)
            ]
            log(f"{phase} {position} done")
        table = pd.concat(frames, ignore_index=True)
        for token_id in table.token_id.unique():
            texts.setdefault(int(token_id), tokenizer.decode([int(token_id)]))
        out[phase] = table.assign(token=table.token_id.map(texts))
    meta = provenance.collect(
        "col lens-judge gemma tokens",
        model="google/gemma-3-27b-it",
        lens_sha256=LENS_SHA256,
        layers=LAYERS,
    )
    for phase, name in (("final", "final_tokens"), ("discussion", "turns_tokens")):
        out[phase].to_parquet(out_dir / f"{name}.parquet", index=False)
        provenance.write_meta(out_dir / f"{name}.parquet", meta)
    return {name: len(t) for name, t in out.items()}
