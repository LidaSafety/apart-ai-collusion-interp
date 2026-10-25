import pandas as pd
import pytest

from colx.jlens.overlap import overlap_table, pairwise_overlap


def test_pairwise_overlap() -> None:
    assert pairwise_overlap([{1, 2}, {1, 2}], k=2) == 1.0
    # Pairs: (a,b) share 1, (a,c) 0, (b,c) 0 → 1 / (2 * 3).
    assert pairwise_overlap([{1, 2}, {1, 3}, {4, 5}], k=2) == pytest.approx(1 / 6)


def test_overlap_table_per_position_and_layer() -> None:
    rows = [
        {"position": "P1", "layer": 24, "run_id": "r", "agent_index": a, "rank": r, "token_id": t}
        for a, ids in enumerate([[1, 2], [1, 3]])
        for r, t in enumerate(ids)
    ]
    table = overlap_table(pd.DataFrame(rows))
    assert table.loc[0, "mean"] == 0.5
