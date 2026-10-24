"""Load the stored residuals of every discussion turn (rounds 1-3) at the plan's 10 layers.

Plan: docs/plans/discussion-turns.md. Same extraction and shard format as round 4
(`colx.extract.stored`). Two read positions per discussion call:
- T-start = `response_start`: the last prompt token before the agent writes its turn;
- T-end = `resp_last`: the last token of the agent's own message.
Only the 10 lens layers are kept, so 1,200 calls x 2 positions fit in about 250 MB (bf16).
"""

from pathlib import Path

import pandas as pd
import torch

from colx.extract.stored import read_shard_rows
from colx.jlens.lens import LAYERS

TURN_POSITIONS = {"T-start": "response_start", "T-end": "resp_last"}


def discussion_calls(samples: pd.DataFrame) -> pd.DataFrame:
    """One row per discussion call (rounds 1-3): run, agent, round and its shard row."""
    calls = samples[samples["phase"] == "discussion"]
    return pd.DataFrame(
        {
            "run_id": calls["run_id"].to_numpy(),
            "agent": calls["agent"].to_numpy(),
            "round": calls["round"].astype(int).to_numpy(),
            "shard_row": calls["sample_idx"].astype(int).to_numpy(),
        }
    ).sort_values(["run_id", "agent", "round"], ignore_index=True)


def load_turns(extract_dir: Path, log=print) -> tuple[pd.DataFrame, torch.Tensor]:
    """Index table and residuals [calls, 2 positions (T-start, T-end), 10 layers, d], bf16."""
    index = discussion_calls(pd.read_parquet(extract_dir / "samples.parquet"))
    blocks, names = [], tuple(TURN_POSITIONS.values())
    groups = list(index.groupby("run_id", sort=True))
    for n, (run_id, group) in enumerate(groups):
        shard = extract_dir / "shards" / f"{run_id}.safetensors"
        blocks.append(
            read_shard_rows(shard, group["shard_row"].tolist(), names)[:, :, list(LAYERS)]
        )
        if n % 10 == 9:
            log(f"read {n + 1}/{len(groups)} shards")
    return index, torch.cat(blocks)
