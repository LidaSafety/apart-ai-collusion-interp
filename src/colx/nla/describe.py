"""Which activations block E describes, and the descriptions table (GPU).

Stored Gemma layer-41 residuals (layer index 5 of the 10 plan layers):
- Core P1 (`results/gemma`): all 400 final calls;
- stego H-start (`results/stego`): the big player's calls and the honest calls made after
  the counter in the same hand, in collusion runs (the S3 units).
Output `nla_descriptions.parquet`: source, run_id, agent, role, hand, label, description.
"""

from pathlib import Path

import pandas as pd
from safetensors.torch import load_file

from colx import provenance
from colx.gemma.model import LAYERS
from colx.nla.verbalize import Verbalizer
from colx.stego.analyse import heard_after_counter

LAYER = 41
BATCH = 32


def core_units(gemma_dir: Path):
    """Core final calls and their P1 layer-41 residuals."""
    calls = pd.read_parquet(gemma_dir / "calls.parquet")
    resid = load_file(str(gemma_dir / "resid.safetensors"))["resid"]
    final = calls[calls.phase == "final"]
    units = final[["run_id", "agent", "role"]].assign(source="core_P1", hand=4, label="")
    return units.reset_index(drop=True), resid[final.index.to_numpy(), 0, LAYERS.index(LAYER)]


def stego_units(stego_dir: Path):
    """Stego S3 units (big player; honest after the counter) and their H-start residuals."""
    calls = pd.read_parquet(stego_dir / "calls.parquet")
    resid = load_file(str(stego_dir / "resid.safetensors"))["resid"]
    keep = calls[calls.role == "big_player"].index.union(heard_after_counter(calls).index)
    sub = calls.loc[keep]
    units = sub[["run_id", "agent", "role", "hand", "label"]].assign(source="stego_H-start")
    return units.reset_index(drop=True), resid[keep.to_numpy(), 0, LAYERS.index(LAYER)]


def describe_all(
    model_dir: Path, gemma_dir: Path, stego_dir: Path, out_dir: Path, log=print
) -> dict:
    """Describe every unit; save the table with provenance."""
    verbalizer = Verbalizer(model_dir)
    frames = []
    for units, vectors in (stego_units(stego_dir), core_units(gemma_dir)):
        texts = []
        for start in range(0, len(units), BATCH):
            texts += verbalizer.describe(vectors[start : start + BATCH])
            log(f"{units.source.iloc[0]}: {len(texts)}/{len(units)}")
        frames.append(units.assign(description=texts))
    table = pd.concat(frames, ignore_index=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    table.to_parquet(out_dir / "nla_descriptions.parquet", index=False)
    provenance.write_meta(
        out_dir / "nla_descriptions.parquet",
        provenance.collect(
            "col lens-judge nla describe", nla="kitft/nla-gemma3-27b-L41-av", layer=LAYER
        ),
    )
    return table.groupby("source").size().to_dict()
