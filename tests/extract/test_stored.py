import json
from pathlib import Path

import pandas as pd
import pytest
import torch
from safetensors.torch import save_file

from colx.extract.stored import final_calls, load_stored

POSITIONS = ["system_end", *[f"quoted_msg_end_{k}" for k in range(13)], "response_start"]


def _samples(run_id: str) -> pd.DataFrame:
    """One private call (row 0) and two final calls (rows 1, 2) quoting 12 messages."""
    rows = []
    for row, (agent, phase) in enumerate([("Ann", "private"), ("Ann", "final"), ("Bo", "final")]):
        quoted = {f"pos_quoted_msg_end_{k}": [100 + k] if k < 12 else None for k in range(13)}
        rows.append(
            {
                "run_id": run_id,
                "agent": agent,
                "phase": phase,
                "sample_idx": row,
                "n_tokens": 500,
                "pos_response_start": [300 + row],
                **quoted,
            }
        )
    return pd.DataFrame(rows)


def _write_extract(root: Path) -> Path:
    """Write a fake extraction whose residual values encode (row, position, block)."""
    (root / "shards").mkdir(parents=True)
    _samples("r1").to_parquet(root / "samples.parquet")
    resid = torch.zeros(3, len(POSITIONS), 4, 8, dtype=torch.bfloat16)
    for row in range(3):
        for pos in range(len(POSITIONS)):
            resid[row, pos] = row * 100 + pos
    tensors = {"resid": resid, "valid": torch.ones(3, len(POSITIONS), dtype=torch.bool)}
    save_file(tensors, str(root / "shards/r1.safetensors"), {"positions": json.dumps(POSITIONS)})
    return root


def test_final_calls_picks_p1_and_p2() -> None:
    calls = final_calls(_samples("r1"))
    assert calls["agent"].tolist() == ["Ann", "Bo"]
    assert calls["p1_token"].tolist() == [301, 302]
    assert calls["p2_token"].tolist() == [111, 111]


def test_final_calls_rejects_wrong_message_count() -> None:
    samples = _samples("r1")
    samples["pos_quoted_msg_end_11"] = None
    with pytest.raises(ValueError):
        final_calls(samples)


def test_load_stored_reads_p1_then_p2(tmp_path: Path) -> None:
    extract = _write_extract(tmp_path / "extract")
    agents = pd.DataFrame({"run_id": ["r1", "r1"], "agent_index": [1, 0], "agent": ["Bo", "Ann"]})
    index, resid = load_stored(extract, agents)
    assert index["agent"].tolist() == ["Ann", "Bo"]  # sorted by agent index
    assert resid.shape == (2, 2, 4, 8)
    p1, p2 = POSITIONS.index("response_start"), POSITIONS.index("quoted_msg_end_11")
    assert resid[0, 0, 0, 0].item() == 100 + p1  # Ann is shard row 1
    assert resid[1, 1, 0, 0].item() == 200 + p2  # Bo is shard row 2
