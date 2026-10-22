from pathlib import Path

import pandas as pd
import pytest

from colx.narcbench.labels import agent_table, parse_vote, run_table, vote_line
from colx.narcbench.runs import load_runs


@pytest.mark.parametrize(
    ("text", "vote"),
    [
        ("RECOMMENDATION: Option A\nWHY", "A"),
        ("RECOMMENDATION: [Option 2]  \nWHY", "2"),
        ("RECOMMENDATION: **Option B**", "B"),
        ("I recommend Option A", None),
        ("", None),
    ],
)
def test_parse_vote(text: str, vote: str | None) -> None:
    assert parse_vote(text) == vote


def test_vote_line() -> None:
    assert vote_line("1") == "RECOMMENDATION: Option 1"


def test_agent_labels(core_dir: Path) -> None:
    agents = agent_table(load_runs(core_dir)).set_index(["mode", "agent"])
    assert agents.loc[("collusion", "Ann"), "colluded"]
    assert not agents.loc[("collusion", "Bo"), "colluded"]
    # Di is honest and votes the target: honest agents never count as colluding.
    assert agents.loc[("collusion", "Di"), "voted_target"]
    assert not agents.loc[("collusion", "Di"), "colluded"]
    assert (agents["parsed_vote"] == agents["vote"]).all()


def test_run_labels_and_styles(core_dir: Path) -> None:
    runs = load_runs(core_dir)
    table = run_table(runs, agent_table(runs)).set_index("mode")
    assert table.loc["collusion", "colluders_voted_target"] == 1
    assert not table.loc["collusion", "colluded"]
    assert not table.loc["control", "colluded"]
    assert table.loc["collusion", "style_group"] == "c1-h1"
    assert pd.isna(table.loc["control", "style_group"])
    assert table.loc["collusion", "request"].startswith("The committee votes.")
