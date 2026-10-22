"""Load the stored round-4 residuals at the two read positions P1 and P2.

The earlier extraction (`/workspace/extract/ours-qwen3_32b/...`, file format learned by
reading its shards and samples table, not its code) saved, per run, one safetensors shard:
`resid` [calls, named positions, 64 blocks, 5120] in bf16, with the position names in the
header metadata. Its `samples.parquet` has one row per call with each position's token index.

- P1 = `response_start`: the last prompt token of the final call, just before the vote.
- P2 = the end of the last quoted message (`quoted_msg_end_11`, the 12th public message):
  the last token of the discussion, before the request to vote.
"""

import json
from pathlib import Path

import pandas as pd
import torch
from safetensors import safe_open
from safetensors.torch import save_file

from colx import provenance

P1_NAME = "response_start"
N_PUBLIC_MESSAGES = 12
P2_NAME = f"quoted_msg_end_{N_PUBLIC_MESSAGES - 1}"
READ_POSITIONS = {"P1": P1_NAME, "P2": P2_NAME}


def _token_index(cell: object) -> int:
    """Return the single token index stored as a one-element list."""
    (index,) = list(cell)
    return int(index)


def final_calls(samples: pd.DataFrame) -> pd.DataFrame:
    """Return one row per final-round call with its shard row and P1/P2 token indices."""
    finals = samples[samples["phase"] == "final"]
    last_quoted = finals[f"pos_{P2_NAME}"]
    beyond = finals[f"pos_quoted_msg_end_{N_PUBLIC_MESSAGES}"]
    if last_quoted.isna().any() or beyond.notna().any():
        raise ValueError(f"final calls do not all quote exactly {N_PUBLIC_MESSAGES} messages")
    return pd.DataFrame(
        {
            "run_id": finals["run_id"].to_numpy(),
            "agent": finals["agent"].to_numpy(),
            "shard_row": finals["sample_idx"].astype(int).to_numpy(),
            "n_tokens": finals["n_tokens"].astype(int).to_numpy(),
            "p1_token": [_token_index(c) for c in finals[f"pos_{P1_NAME}"]],
            "p2_token": [_token_index(c) for c in last_quoted],
        }
    )


def _shard_positions(shard: Path) -> list[str]:
    """Return the shard's named positions, in its position-axis order."""
    with safe_open(str(shard), "pt") as f:
        return json.loads(f.metadata()["positions"])


def read_shard_rows(shard: Path, rows: list[int]) -> torch.Tensor:
    """Read the residuals of `rows` at P1 and P2: [len(rows), 2, blocks, d_model], bf16."""
    names = _shard_positions(shard)
    columns = [names.index(READ_POSITIONS["P1"]), names.index(READ_POSITIONS["P2"])]
    with safe_open(str(shard), "pt") as f:
        resid = f.get_slice("resid")
        valid = f.get_tensor("valid")
        picked = [torch.stack([resid[r : r + 1, c : c + 1][0, 0] for c in columns]) for r in rows]
    if not all(bool(valid[r, c]) for r in rows for c in columns):
        raise ValueError(f"{shard.name}: a requested position is not stored")
    return torch.stack(picked)


def load_stored(extract_dir: Path, agents: pd.DataFrame) -> tuple[pd.DataFrame, torch.Tensor]:
    """Load P1/P2 residuals for every agent, sorted by run id and agent index.

    Returns the index table (agent table keys plus shard rows and token indices) and a
    tensor [agents, 2 positions (P1, P2), 64 blocks, 5120].
    """
    calls = final_calls(pd.read_parquet(extract_dir / "samples.parquet"))
    index = (
        agents[["run_id", "agent_index", "agent"]]
        .merge(calls, on=["run_id", "agent"], how="left", validate="one_to_one")
        .sort_values(["run_id", "agent_index"], ignore_index=True)
    )
    if index["shard_row"].isna().any():
        raise ValueError("some agents have no stored final call")
    blocks = []
    for run_id, group in index.groupby("run_id", sort=True):
        shard = extract_dir / "shards" / f"{run_id}.safetensors"
        blocks.append(read_shard_rows(shard, group["shard_row"].tolist()))
    return index, torch.cat(blocks)


def write_stored(extract_dir: Path, out_dir: Path) -> dict[str, object]:
    """Save P1/P2 residuals (`activations.safetensors`) and their index table."""
    agents = pd.read_parquet(out_dir / "agents.parquet")
    index, resid = load_stored(extract_dir, agents)
    resid_path = out_dir / "activations.safetensors"
    save_file({"resid": resid.contiguous()}, str(resid_path), metadata={"positions": "P1,P2"})
    index_path = out_dir / "activations_index.parquet"
    index.to_parquet(index_path, index=False)
    meta = provenance.collect(
        "col lens-judge activations",
        extract_dir=str(extract_dir),
        positions=READ_POSITIONS,
        shape=list(resid.shape),
    )
    for path in (resid_path, index_path):
        provenance.write_meta(path, meta)
    return {"agents": len(index), "shape": tuple(resid.shape), "dtype": str(resid.dtype)}
