import pandas as pd

from colx.analysis.data import run_scores
from colx.analysis.suite import instrument_tests, vs_baselines


def test_run_scores_mean_of_top_two(table: pd.DataFrame) -> None:
    runs = run_scores(table, "score_B").set_index("run_id")
    expected = table[table.run_id == "s1_collusion"].score_B.nlargest(2).mean()
    assert runs.loc["s1_collusion", "run_score"] == expected
    assert len(runs) == 12


def test_instrument_tests_find_the_planted_signal(table: pd.DataFrame) -> None:
    records, _ = instrument_tests(table, ("lens", "raw", "P1"), "score_B", n_boot=200, n_perm=200)
    by = {r["test"]: r for r in records}
    assert by["a"]["auroc"] == 1.0 and by["b"]["auroc"] == 1.0
    assert by["a"]["n_pos"] == 4 and by["a"]["n_neg"] == 8  # s0, s3 collusion runs split
    assert by["split"]["wins"] == 2 and by["split"]["losses"] == 0
    assert by["paired_by_scenario"]["wins"] == 4
    assert by["operating_point"]["recall"] == 1.0


def test_vs_baselines_beats_a_flat_baseline(table: pd.DataFrame) -> None:
    lens_runs = run_scores(table, "score_B")
    flat = lens_runs.assign(run_score=0.5)
    out = vs_baselines(lens_runs, {"vote": flat}, n_boot=200)[0]
    assert out["test"] == "b_vs_vote" and out["diff"] == 0.5 and out["beats"]
