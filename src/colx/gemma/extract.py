"""Residuals of every agent call at its read points, through Gemma (GPU).

One forward pass per call over the rendered prompt plus the reply (as the Qwen extraction
did), with hooks on the 10 plan layers. Read points (token indices into that sequence):
- `start`: the last prompt token (P1 for final calls, T-start for discussion calls);
- `end`: the last reply token (T-end for discussion calls);
- `p2`: final calls only, the last token of the quoted discussion (end of the last public
  message), found through the tokenizer's character offsets.
Output: `calls.parquet` (one row per call, its token indices) and `resid.safetensors`
[calls, 3 read points, 10 layers, d] in bf16 (p2 is zeros for non-final calls).
"""

import time
from pathlib import Path

import pandas as pd
import torch
from safetensors.torch import save_file

from colx.gemma.calls import load_calls
from colx.gemma.model import LAYERS, decoder_layers, render

POINTS = ("start", "end", "p2")


def p2_index(offsets: list[tuple[int, int]], text: str, last_message: str) -> int:
    """Index of the token that ends the last quoted public message in `text`."""
    end = text.rfind(last_message) + len(last_message)
    if end < len(last_message):
        raise ValueError("last public message not found in the prompt")
    return max(i for i, (a, _) in enumerate(offsets) if a < end)


def read_points(
    tokenizer, call: dict, last_message: str | None, render_fn=render
) -> tuple[list[int], dict]:
    """Token ids of prompt + reply, and the token index of each read point."""
    prompt = render_fn(tokenizer, call["system"], call["user"])
    full = prompt + call["reply"]
    enc = tokenizer(full, add_special_tokens=False, return_offsets_mapping=True)
    n_prompt = len(tokenizer(prompt, add_special_tokens=False)["input_ids"])
    points = {"start": n_prompt - 1, "end": len(enc["input_ids"]) - 1, "p2": -1}
    if last_message is not None:
        points["p2"] = p2_index(enc["offset_mapping"], prompt, last_message)
    return enc["input_ids"], points


@torch.inference_mode()
def forward_points(
    model, ids: list[int], points: dict, blocks=None, layers: tuple[int, ...] = LAYERS
) -> torch.Tensor:
    """Block outputs at the read points for the plan layers: [3, 10, d] bf16 (CPU)."""
    captured = {}
    hooks = [
        (blocks if blocks is not None else decoder_layers(model))[layer].register_forward_hook(
            lambda _m, _i, out, layer=layer: captured.__setitem__(
                layer, out[0] if isinstance(out, tuple) else out
            )
        )
        for layer in layers
    ]
    try:
        model(input_ids=torch.tensor([ids], device=model.device), use_cache=False)
    finally:
        for h in hooks:
            h.remove()
    idx = torch.tensor([max(points[p], 0) for p in POINTS], device=model.device)
    out = torch.stack([captured[layer][0, idx] for layer in layers], dim=1)
    if points["p2"] < 0:
        out[2] = 0
    return out.to(torch.bfloat16).cpu()


def extract(
    core_dir: Path, model_dir: Path, out_dir: Path, log=print, backend: str = "gemma"
) -> dict:
    """Forward every call of every run; save the index table and residuals."""
    from colx.backends import BACKENDS

    be = BACKENDS[backend]
    tokenizer, model = be.load(model_dir)
    blocks = be.blocks(model)
    rows, tensors, start = [], [], time.time()
    runs = sorted(p for p in core_dir.iterdir() if p.is_dir())
    for n, run_dir in enumerate(runs):
        results = pd.read_json(run_dir / "results.json", typ="series")
        last = results["public_messages"][-1]
        for call in load_calls(run_dir):
            if call["phase"] == "private":
                continue
            last_msg = last if call["phase"] == "final" else None
            ids, points = read_points(tokenizer, call, last_msg, render_fn=be.render)
            tensors.append(forward_points(model, ids, points, blocks, be.layers))
            rows.append(
                {k: call[k] for k in ("run_id", "agent", "role", "phase", "round")}
                | {f"pos_{p}": points[p] for p in POINTS}
                | {"n_tokens": len(ids)}
            )
        log(f"run {n + 1}/{len(runs)} ({time.time() - start:.0f}s)")
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(out_dir / "calls.parquet", index=False)
    save_file({"resid": torch.stack(tensors).contiguous()}, str(out_dir / "resid.safetensors"))
    return {"calls": len(rows), "shape": (len(tensors), *tensors[0].shape)}
