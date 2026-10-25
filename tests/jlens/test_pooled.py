import pandas as pd

from colx.jlens.pooled import pooled_table, pooled_tokens, render_pooled


def _rows() -> pd.DataFrame:
    # Two layers, three ranks each; "secret" is top at both (once with a leading space).
    return pd.DataFrame(
        {
            "layer": [24, 24, 24, 58, 58, 58],
            "rank": [0, 1, 2, 0, 1, 2],
            "token": ["secret", "plan", "B", " secret", "hide", "plan"],
        }
    )


def test_pooled_tokens_merge_spaces_and_count_layers() -> None:
    assert pooled_tokens(_rows()) == [("secret", 2), ("plan", 2), ("hide", 1), ("B", 1)]


def test_pooled_tokens_keep_k_best_by_rank_not_score() -> None:
    assert pooled_tokens(_rows(), k=2) == [("secret", 2), ("plan", 2)]


def test_pooled_ties_broken_by_earliest_layer() -> None:
    rows = pd.DataFrame({"layer": [58, 24], "rank": [0, 0], "token": ["late", "early"]})
    assert [t for t, _ in pooled_tokens(rows)] == ["early", "late"]


def test_pooled_tokens_drop_digits() -> None:
    rows = pd.DataFrame({"layer": [24, 24], "rank": [0, 1], "token": [" 3", "plan"]})
    assert pooled_tokens(rows) == [("plan", 1)]


def test_render_pooled_marks_repeats() -> None:
    assert render_pooled([("secret", 2), ("B", 1)]) == "secret (2 layers), B"


def test_pooled_table_one_row_per_agent_and_position() -> None:
    one = _rows().assign(run_id="r", agent="Ann")
    table = pd.concat([one.assign(agent_index=i, position=p) for i in (0, 1) for p in ("P1", "P2")])
    out = pooled_table(table)
    assert len(out) == 4
    assert out.pooled.iloc[0].startswith("secret (2 layers), plan (2 layers)")
