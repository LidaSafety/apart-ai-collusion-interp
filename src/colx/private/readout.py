"""Lens tokens of each colluder's private-channel call (round 0) on Qwen Core (CPU or GPU).

Stored extraction (`/workspace/extract/ours-qwen3_32b/qwen3_32b/core`, the same as the
discussion turns): the 100 private calls, at `response_start` (P-start: before the colluder
writes its private message) and `resp_last` (P-end: its last token). Same lens, layers and
renderings as the discussion turns; words-relative = relative to the mean over the 100
private calls. Output `private_tokens.parquet` in the discussion-turns schema (round 0).
"""

from pathlib import Path

import pandas as pd
import torch

from colx import provenance, qwen
from colx.extract.stored import read_shard_rows
from colx.jlens.lens import LAYERS, load_maps
from colx.turns.tokens import token_table
from colx.unembed import from_checkpoint

POSITIONS = {"P-start": "response_start", "P-end": "resp_last"}


def private_residuals(extract_dir: Path) -> tuple[pd.DataFrame, torch.Tensor]:
    """The 100 private calls (sorted) and their residuals: [n, 2 positions, 10 layers, d]."""
    s = pd.read_parquet(extract_dir / "samples.parquet")
    calls = s[s.phase == "private"].sort_values(["run_id", "agent"], ignore_index=True)
    blocks = []
    for run_id, g in calls.groupby("run_id", sort=True):
        shard = extract_dir / "shards" / f"{run_id}.safetensors"
        rows = read_shard_rows(shard, g.sample_idx.astype(int).tolist(), tuple(POSITIONS.values()))
        blocks.append(rows[:, :, list(LAYERS)])
    index = calls[["run_id", "agent"]].assign(round=0)
    return index, torch.cat(blocks)


def write_private_tokens(
    extract_dir: Path, model_dir: Path, lens_path: Path, out_dir: Path, log=print
) -> dict:
    """Read, render both views, save `private_tokens.parquet` with provenance."""
    index, resid = private_residuals(extract_dir)
    table = token_table(
        index,
        resid,
        load_maps(lens_path),
        from_checkpoint(model_dir),
        qwen.load_tokenizer(str(model_dir)),
        log,
    )
    table["position"] = table.position.map(dict(zip(("T-start", "T-end"), POSITIONS, strict=True)))
    out_dir.mkdir(parents=True, exist_ok=True)
    table.to_parquet(out_dir / "private_tokens.parquet", index=False)
    provenance.write_meta(
        out_dir / "private_tokens.parquet",
        provenance.collect("col lens-judge private tokens", label="exploratory"),
    )
    return {"calls": len(index), "rows": len(table)}
