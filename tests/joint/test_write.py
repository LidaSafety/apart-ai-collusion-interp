import pandas as pd

from colx.joint.write import joint_runs, primary_family


def test_joint_runs_key_by_arm_and_position_with_labels() -> None:
    scores = pd.DataFrame(
        {
            "arm": ["lens", "lens", "discussion"],
            "position": ["P1", "P1", "-"],
            "run_id": ["r1", "r2", "r1"],
            "rating": [7.0, 2.0, 5.0],
        }
    )
    runs = pd.DataFrame(
        {
            "run_id": ["r1", "r2"],
            "scenario_id": ["s", "s"],
            "mode": ["collusion", "control"],
            "style_group": [0, 0],
            "colluded": [True, False],
        }
    )
    out = joint_runs(scores, runs)
    assert set(out) == {("lens", "P1"), ("discussion", "-")}
    lens = out[("lens", "P1")].set_index("run_id")
    assert lens.loc["r1", "run_score"] == 7.0 and bool(lens.loc["r1", "run_colluded"])


def test_primary_family_has_six_tests_and_applies_holm() -> None:
    tests = [
        {"arm": "lens", "position": p, "test": t, "p": 0.001, "auroc": 0.8}
        for p in ("P1", "P2")
        for t in ("a", "b")
    ]
    tests.append({"arm": "lens", "position": "P1", "test": "b_style", "p": 0.0})
    diffs = [
        {"x": f"both_{p}", "y": "discussion", "test": "b", "p": 0.5, "diff": 0.0}
        for p in ("P1", "P2")
    ]
    diffs.append({"x": "both_P1", "y": "discussion", "test": "a", "p": 0.0, "diff": 0.1})
    family = {r["name"]: r for r in primary_family(tests, diffs)}
    assert len(family) == 6
    assert family["lens_P1_a"]["holm_rejected"]
    assert not family["both_P1_minus_discussion_b"]["holm_rejected"]
