import pandas as pd

from colx.joint.pairs import (
    agreement,
    agreement_table,
    exclusive_counts,
    overlap_score,
    overlap_table,
)


def test_agreement_counts_the_most_named_pair() -> None:
    assert agreement([(1, 3), (2, 4), (1, 3), None]) == (2, (1, 3))


def test_agreement_tie_goes_to_the_earliest() -> None:
    assert agreement([(2, 4), (1, 3), None, None]) == (1, (2, 4))
    assert agreement([None, None]) == (0, None)


SETS = [{"a", "b", "x"}, {"c"}, {"a", "b", "y"}, {"x", "c"}]


def test_exclusive_counts_ignore_entries_others_have() -> None:
    counts = exclusive_counts(SETS)
    assert counts[(1, 3)] == 2  # a, b
    assert counts[(1, 4)] == 1  # x
    assert counts[(2, 4)] == 1  # c
    assert counts[(1, 2)] == 0


def test_overlap_score_is_largest_minus_median() -> None:
    # Counts: (1,2)=0 (1,3)=2 (1,4)=1 (2,3)=0 (2,4)=1 (3,4)=0 -> median 0.5.
    assert overlap_score(SETS) == (1.5, (1, 3))


def test_overlap_score_tie_goes_to_lowest_numbers() -> None:
    assert overlap_score([{"a"}, {"a"}, {"b"}, {"b"}])[1] == (1, 2)


def test_agreement_table_one_row_per_run() -> None:
    rows = [
        ("lens_rel", "P1", [1, 2]),
        ("lens_pooled", "P1", [1, 2]),
        ("lens_rel", "P2", [3, 4]),
        ("lens_pooled", "P2", None),
        ("discussion", "-", [3, 4]),
    ]
    scores = pd.DataFrame(
        [
            {"run_id": "r", "arm": a, "position": p, "pair": pr, "order": ["A", "B", "C", "D"]}
            for a, p, pr in rows
        ]
    )
    out = agreement_table(scores).iloc[0]
    assert out.run_score == 2.0 and out.pair == (1, 2)


def test_overlap_table_uses_the_prompt_order() -> None:
    tokens = pd.DataFrame(
        {
            "run_id": "r",
            "position": "P1",
            "layer": 24,
            "agent": ["A", "B", "C", "D"],
            "token_id": [7, 9, 7, 8],
        }
    )
    out = overlap_table(tokens, {"r": ["C", "B", "A", "D"]}, "P1").iloc[0]
    assert out.pair == (1, 3) and out.run_score == 1.0
