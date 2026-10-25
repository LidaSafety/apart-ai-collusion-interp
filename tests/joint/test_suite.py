import pandas as pd
import pytest

from colx.joint.suite import colluder_pair, compare, instrument_tests, pair_found, subset


def _runs(score_of) -> pd.DataFrame:
    """6 scenarios x {collusion, control}; the first 4 collusion-mode runs colluded."""
    rows = []
    for s in range(6):
        for mode in ("collusion", "control"):
            colluded = mode == "collusion" and s < 4
            rows.append(
                {
                    "run_id": f"s{s}_{mode}",
                    "scenario_id": f"s{s}",
                    "mode": mode,
                    "style_group": s % 2,
                    "run_colluded": colluded,
                    "run_score": score_of(s, mode, colluded),
                }
            )
    return pd.DataFrame(rows)


PERFECT = _runs(lambda s, mode, c: 1.0 if c else 0.0)
INSTRUCTION_ONLY = _runs(lambda s, mode, c: 1.0 if mode == "collusion" else 0.0)


def test_subset_b_keeps_collusion_mode_runs() -> None:
    assert len(subset(PERFECT, "a")) == 12 and len(subset(PERFECT, "b")) == 6


def test_perfect_scores_give_auroc_one_and_full_recall() -> None:
    tests = {t["test"]: t for t in instrument_tests(PERFECT, n_boot=50, n_perm=50)}
    assert tests["a"]["auroc"] == 1.0 and tests["b"]["auroc"] == 1.0
    assert tests["operating_point"]["recall"] == 1.0
    assert tests["paired_by_scenario"]["wins"] == 4


def test_instruction_only_scores_are_chance_on_b() -> None:
    tests = {t["test"]: t for t in instrument_tests(INSTRUCTION_ONLY, n_boot=50, n_perm=50)}
    assert tests["b"]["auroc"] == 0.5
    # (4 * 6 + 0.5 * 4 * 2) / (4 * 8): every colluded run beats the 6 controls, ties the 2.
    assert tests["a"]["auroc"] == pytest.approx(0.875)


def test_compare_perfect_minus_instruction_only_on_b() -> None:
    rec = compare(PERFECT, INSTRUCTION_ONLY, "b", n_boot=50)
    assert rec["diff"] == 0.5 and rec["test"] == "b"


def test_colluder_pair_uses_prompt_order() -> None:
    roles = {"Ann": "honest", "Bo": "colluder", "Cy": "honest", "Di": "colluder"}
    assert colluder_pair(["Di", "Ann", "Bo", "Cy"], roles) == (1, 3)


def test_pair_found_counts_exact_pairs_in_collusion_mode_runs() -> None:
    roles = pd.Series(
        {
            r: {"A": "colluder", "B": "colluder", "C": "honest", "D": "honest"}
            for r in ("r1", "r2", "r3")
        }
    )
    colluded = pd.Series({"r1": True, "r2": False})  # r3 is a control run
    scores = pd.DataFrame(
        {
            "run_id": ["r1", "r2", "r3"],
            "order": [["A", "C", "B", "D"]] * 3,
            "pair": [[1, 3], [1, 2], [1, 3]],
        }
    )
    found = {r["group"]: r for r in pair_found(scores, roles, colluded)}
    assert (found["all"]["found"], found["all"]["n"]) == (1, 2)
    assert found["colluded"]["share"] == 1.0 and found["not_colluded"]["share"] == 0.0
