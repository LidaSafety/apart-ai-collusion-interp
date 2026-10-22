from pathlib import Path

from colx.narcbench.labels import agent_table, run_table
from colx.narcbench.runs import load_runs
from colx.narcbench.summary import label_summary, split_run_styles


def _tables(core_dir: Path):
    runs = load_runs(core_dir)
    agents = agent_table(runs)
    return agents, run_table(runs, agents)


def test_label_summary_counts(core_dir: Path) -> None:
    counts = label_summary(*_tables(core_dir))
    assert counts["runs_colluded"] == 0
    assert counts["collusion_runs_1_voted"] == 1
    assert counts["colluders_voted_target"] == 1
    assert counts["honest_in_collusion_runs_voted_target"] == 1
    assert counts["control_agents_voted_target"] == 0
    assert counts["replies_start_recommendation"] == 8
    assert counts["replies_start_recommendation_option"] == 0


def test_split_run_styles(core_dir: Path) -> None:
    # Ann (standard) voted the target, Bo (lowkey) did not.
    assert split_run_styles(*_tables(core_dir)) == {
        "split_runs": 1,
        "same_style": 0,
        "voter_standard_other_lowkey": 1,
        "other": 0,
    }
