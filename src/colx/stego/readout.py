"""Read the stego residuals through the Gemma lens: raw and words-relative top 25.

The same rules as the Gemma Core readout (`colx.gemma.readout.point_rows`); words-relative is
relative to the mean over all player calls of the same hand number. Output
`tokens.parquet`: run_id, mode, agent, role, hand, label, position (H-start, H-end), layer,
rendering, rank, token_id, token.
"""

from pathlib import Path

import pandas as pd
import torch
from safetensors.torch import load_file

from colx import provenance
from colx.gemma.model import LAYERS, LENS_SHA256, Unembed, load
from colx.gemma.readout import point_rows
from colx.jlens.filtered import word_mask
from colx.jlens.lens import load_maps, sha256_of
from colx.jlens.render import printable_mask

READS = {"H-start": "start", "H-end": "end"}


def write_tokens(model_dir: Path, lens_path: Path, out_dir: Path, log=print) -> dict:
    """Check the lens hash, read every call out at both read points, save the table."""
    if sha256_of(lens_path) != LENS_SHA256:
        raise ValueError("Gemma lens sha256 does not match")
    calls = pd.read_parquet(out_dir / "calls.parquet")
    resid = load_file(str(out_dir / "resid.safetensors"))["resid"]
    tokenizer, model = load(model_dir)
    unembed, vocab = Unembed(model), model.lm_head.weight.shape[0]
    masks = {"raw": printable_mask(tokenizer, vocab), "rel": word_mask(tokenizer, vocab)}
    maps = {layer: m.to(model.device) for layer, m in load_maps(lens_path, LAYERS).items()}
    keep = calls[["run_id", "mode", "agent", "role", "hand", "label"]].reset_index(drop=True)
    groups = torch.as_tensor(calls["hand"].to_numpy())
    frames = []
    for position, point in READS.items():
        frames += [
            f.assign(position=position)
            for f in point_rows(keep, resid, groups, point, maps, unembed, masks)
        ]
        log(f"{position} done")
    table = pd.concat(frames, ignore_index=True)
    texts = {int(t): tokenizer.decode([int(t)]) for t in table.token_id.unique()}
    table = table.assign(token=table.token_id.map(texts))
    table.to_parquet(out_dir / "tokens.parquet", index=False)
    provenance.write_meta(
        out_dir / "tokens.parquet",
        provenance.collect("col lens-judge stego tokens", lens_sha256=LENS_SHA256),
    )
    return {"rows": len(table)}
