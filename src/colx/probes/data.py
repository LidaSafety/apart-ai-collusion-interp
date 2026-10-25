"""Activation sets in NARCBench's probe-input format: a metadata list plus per-layer arrays.

NARCBench's `reproduce_LR` reads `meta` (one dict per agent call: run_id, agent_name,
role, phase, channel, mode) and an npz-like mapping `layer_<l>` -> [calls, d]. We build
the same structure from two sources:
- Qwen3-32B: our stored extraction, position `chat_end`, which equals the last token of
  NARCBench's `_build_gen_text` rendering (checked on all 1,600 public Core calls);
- Gemma-3-27B-IT: a fresh extraction with their own rendering and hooks (`extract.py`).
Only public-channel calls are kept: the probes never read the private channel.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from colx.extract.stored import read_shard_rows

QWEN_POSITION = "chat_end"
META_KEYS = ("run_id", "agent_name", "role", "phase", "channel", "mode")


def stored_set(extract_dir: Path, layers: list[int], phases: tuple[str, ...]) -> tuple[list, dict]:
    """Public calls of the given phases from a stored extraction, in their format."""
    s = pd.read_parquet(extract_dir / "samples.parquet")
    s = s[(s.channel == "public") & s.phase.isin(phases)].sort_values(["run_id", "sample_idx"])
    meta, blocks = [], []
    for run_id, g in s.groupby("run_id", sort=True):
        shard = extract_dir / "shards" / f"{run_id}.safetensors"
        rows = read_shard_rows(shard, g.sample_idx.astype(int).tolist(), (QWEN_POSITION,))
        blocks.append(rows[:, 0][:, layers].float().numpy())
        meta += [
            {
                "run_id": r.run_id,
                "agent_name": r.agent,
                "role": r.role,
                "phase": r.phase,
                "channel": r.channel,
                "mode": r["mode"],
            }
            for _, r in g.iterrows()
        ]
    acts = np.concatenate(blocks)
    return meta, {f"layer_{layer}": acts[:, i] for i, layer in enumerate(layers)}


def save_set(meta: list, arrays: dict, folder: Path) -> None:
    """Write a set as NARCBench does: `metadata_gen.json` and `activations_gen.npz`."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "metadata_gen.json").write_text(json.dumps(meta))
    np.savez(folder / "activations_gen.npz", **arrays)


def load_set(folder: Path) -> tuple[list, dict]:
    """Read a saved set (their `load_data`, without their path conventions)."""
    meta = json.loads((folder / "metadata_gen.json").read_text())
    npz = np.load(folder / "activations_gen.npz")
    return meta, {k: npz[k] for k in npz.files}


def merge_sets(*sets: tuple[list, dict]) -> tuple[list, dict]:
    """Concatenate several sets (same layers) into one."""
    meta = [m for s in sets for m in s[0]]
    keys = sets[0][1].keys()
    return meta, {k: np.concatenate([s[1][k] for s in sets]) for k in keys}
