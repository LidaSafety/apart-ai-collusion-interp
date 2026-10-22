import pandas as pd
import pytest

from colx.analysis.summary import MEANINGS, primary_family, reading, verdict

ALL = {"text": True, "instruction_only": True, "vote": True}


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ((0.6, 0.9, True), "above"),
        ((0.2, 0.45, False), "below"),
        ((0.4, 0.7, False), "inconclusive"),
        ((0.55, 0.8, False), "not above (Holm)"),
    ],
)
def test_verdict(args: tuple, expected: str) -> None:
    assert verdict(*args) == expected


@pytest.mark.parametrize(
    ("gate", "a", "b", "style_p", "beats", "key"),
    [
        (True, "above", "below", 0.5, ALL, "reversed"),
        (False, "above", "inconclusive", 0.5, ALL, "gate_fail_b_not"),
        (False, "inconclusive", "above", 0.5, ALL, "gate_fail_b_above"),
        (True, "inconclusive", "inconclusive", 0.5, ALL, "a_not_b_not"),
        (True, "above", "inconclusive", 0.5, ALL, "a_above_b_not"),
        (True, "above", "above", 0.2, ALL, "not_beyond_style"),
        (True, "above", "above", 0.01, ALL | {"text": False}, "not_beyond_text"),
        (True, "above", "above", 0.01, ALL | {"vote": False}, "not_beyond_vote"),
        (True, "above", "above", 0.01, ALL, "beyond_all"),
    ],
)
def test_reading_follows_the_plan_table(gate, a, b, style_p, beats, key) -> None:
    assert reading(gate, a, b, style_p, beats) == key
    assert key in MEANINGS


def test_primary_family_holm_over_eight() -> None:
    rows = [
        {"judge": "lens", "score": "score_B", "test": t, "arm": arm, "position": pos,
         "p": 0.001 if (t, arm, pos) == ("a", "rel", "P2") else 0.5, "ci_low": 0.4, "ci_high": 0.7}
        for t in ("a", "b") for arm in ("raw", "rel") for pos in ("P1", "P2")
    ]  # fmt: skip
    out = primary_family(pd.DataFrame(rows))
    assert len(out) == 8
    assert out.holm_rejected.sum() == 1
    assert set(out.verdict) == {"above", "inconclusive"}
