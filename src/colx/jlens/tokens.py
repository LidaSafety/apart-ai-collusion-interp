"""Read every stored round-4 residual through the J-lens: top-25 tokens per layer.

Output `lens_tokens.parquet`: one row per (agent, position, layer, rank) with the token id,
its decoded text and its lens probability (softmax over the full vocabulary, so the
probabilities of the shown tokens need not sum to 1). `lens_grids.parquet` holds the
rendered grid (10 lines of 25 tokens) per agent and position, as the judge will see it.
`lens_overlap.parquet` holds how much a run's four agents share their top-25 lists.
"""

from pathlib import Path

import pandas as pd
import torch
from safetensors.torch import load_file

from colx import provenance, qwen
from colx.jlens.lens import LAYERS, load_maps, readout, sha256_of
from colx.jlens.overlap import overlap_table
from colx.jlens.render import TOP_K, printable_mask, render_grid, top_tokens
from colx.unembed import Unembed, from_checkpoint

POSITIONS = ("P1", "P2")


def layer_top_tokens(
    resid: torch.Tensor, jmap: torch.Tensor, unembed: Unembed, mask: torch.Tensor
) -> tuple[torch.Tensor, torch.Tensor]:
    """Top-k printable ids and their lens probabilities for residuals [n, d]: two [n, k]."""
    logits = readout(resid, jmap, unembed)
    ids = top_tokens(logits, mask)
    probs = torch.softmax(logits, dim=-1).gather(-1, ids)
    return ids.cpu(), probs.cpu()


def token_rows(
    index: pd.DataFrame, position: str, layer: int, ids: torch.Tensor, probs: torch.Tensor, decode
) -> list[dict]:
    """Flatten one (position, layer) readout into table rows."""
    rows = []
    for i, agent in enumerate(index.itertuples()):
        for rank in range(ids.shape[1]):
            token_id = int(ids[i, rank])
            rows.append(
                {
                    "run_id": agent.run_id,
                    "agent_index": agent.agent_index,
                    "agent": agent.agent,
                    "position": position,
                    "layer": layer,
                    "rank": rank,
                    "token_id": token_id,
                    "token": decode(token_id),
                    "prob": float(probs[i, rank]),
                }
            )
    return rows


def grids(tokens: pd.DataFrame) -> pd.DataFrame:
    """Render each agent's grid per position from the token table."""
    rows = []
    keys = ["run_id", "agent_index", "agent", "position"]
    for key, group in tokens.sort_values([*keys, "layer", "rank"]).groupby(keys, sort=False):
        lines = {layer: g["token"].tolist() for layer, g in group.groupby("layer")}
        rows.append(dict(zip(keys, key, strict=True)) | {"grid": render_grid(lines)})
    return pd.DataFrame(rows)


def compute_lens_tokens(
    model_dir: Path, lens_path: Path, out_dir: Path, device: str
) -> pd.DataFrame:
    """Read all stored P1/P2 residuals through the lens at the 10 layers."""
    index = pd.read_parquet(out_dir / "activations_index.parquet")
    resid = load_file(str(out_dir / "activations.safetensors"))["resid"]
    tokenizer = qwen.load_tokenizer(str(model_dir))
    unembed = from_checkpoint(model_dir, device=device)
    mask = printable_mask(tokenizer, unembed.lm_head.shape[0])
    maps = load_maps(lens_path)
    decode = lambda token_id: tokenizer.decode([token_id])  # noqa: E731 (tiny local alias)
    rows = []
    for layer in LAYERS:
        jmap = maps[layer].to(device)
        for p, position in enumerate(POSITIONS):
            ids, probs = layer_top_tokens(resid[:, p, layer], jmap, unembed, mask)
            rows += token_rows(index, position, layer, ids, probs, decode)
    return pd.DataFrame(rows)


def write_lens_tokens(model_dir: Path, lens_path: Path, out_dir: Path, device: str) -> dict:
    """Check the lens file's hash, compute the token table and grids, save with provenance."""
    digest = sha256_of(lens_path)
    if digest != provenance.LENS_SHA256:
        raise ValueError(f"lens sha256 {digest} != expected {provenance.LENS_SHA256}")
    tokens = compute_lens_tokens(model_dir, lens_path, out_dir, device)
    meta = provenance.collect(
        "col lens-judge lens-tokens", layers=LAYERS, top_k=TOP_K, lens_path=str(lens_path)
    )
    outputs = {
        "lens_tokens": tokens,
        "lens_grids": grids(tokens),
        "lens_overlap": overlap_table(tokens),
    }
    for name, table in outputs.items():
        path = out_dir / f"{name}.parquet"
        table.to_parquet(path, index=False)
        provenance.write_meta(path, meta)
    return {"rows": len(tokens), "lens_sha256": digest}
