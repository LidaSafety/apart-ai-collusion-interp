"""Residuals of every stego player call at H-start and H-end, through Gemma (GPU).

The same forward pass and hooks as the Gemma Core extraction (`colx.gemma.extract`):
prompt + reply, 10 plan layers. Read points: H-start = the last prompt token (before the
player's table talk and bet), H-end = the last reply token. Output: `calls.parquet` and
`resid.safetensors` [calls, 2, 10, d] bf16.
"""

import time
from pathlib import Path

import pandas as pd
import torch
from safetensors.torch import save_file

from colx.backends import BACKENDS
from colx.gemma.extract import forward_points, read_points
from colx.stego.calls import load_stego_calls

KEEP = ["run_id", "mode", "agent", "role", "hand", "label"]


def extract(
    stego_dir: Path, model_dir: Path, out_dir: Path, backend: str = "gemma", log=print
) -> dict:
    """Forward every player call of every run; save the index table and residuals."""
    be = BACKENDS[backend]
    tokenizer, model = be.load(model_dir)
    blocks = be.blocks(model)
    rows, tensors, start = [], [], time.time()
    runs = sorted(p for p in stego_dir.iterdir() if p.is_dir())
    for n, run_dir in enumerate(runs):
        for call in load_stego_calls(run_dir):
            ids, points = read_points(tokenizer, call, None, render_fn=be.render)
            tensors.append(forward_points(model, ids, points, blocks, be.layers)[:2])
            rows.append(
                {k: call[k] for k in KEEP}
                | {"pos_start": points["start"], "pos_end": points["end"], "n_tokens": len(ids)}
            )
        if n % 10 == 9 or n == len(runs) - 1:
            log(f"run {n + 1}/{len(runs)} ({time.time() - start:.0f}s)")
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(out_dir / "calls.parquet", index=False)
    save_file({"resid": torch.stack(tensors).contiguous()}, str(out_dir / "resid.safetensors"))
    return {"calls": len(rows), "shape": (len(tensors), *tensors[0].shape)}
