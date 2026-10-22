import pandas as pd

from colx.analysis.checks import instruction_controls, judge_works, name_control
from colx.analysis.descriptive import vote_label_share

from .conftest import make_table


def test_judge_works_and_instruction_controls() -> None:
    works = make_table("judge_works", "-", "-")
    out = judge_works(works, n_boot=100, n_perm=100)
    assert out["n_pos"] == 12 and out["n_neg"] == 36
    control = make_table("instruction_control", "raw", "P1")
    control = control[control["mode"] == "collusion"]
    checks = {c["check"]: c for c in instruction_controls(control, n_boot=100, n_perm=100)}
    vote_free = checks["instruction_control_vote_free"]
    # Colluders who did not vote the target (s0, s3: 1 each) vs the 12 honest agents.
    assert vote_free["n_pos"] == 2 and vote_free["n_neg"] == 12


def test_name_control_accuracy() -> None:
    rows = [
        {"kind": "number", "arm": "raw", "true_number": t,
         "p_1": float(t == 1), "p_2": float(t == 2), "p_3": 0.5, "p_4": 0.0}
        for t in (1, 2, 3, 4)
    ]  # fmt: skip
    out = name_control(pd.DataFrame(rows))[0]
    assert out["accuracy"] == 0.75 and out["n"] == 4


def test_vote_label_share() -> None:
    tokens = pd.DataFrame(
        {"position": "P1", "layer": 24, "run_id": "r", "agent_index": [0, 0, 1, 1],
         "token": [" B", "x", " A", " B"]}
    )  # fmt: skip
    agents = pd.DataFrame({"run_id": "r", "agent_index": [0, 1], "vote": ["B", "B"]})
    runs = pd.DataFrame({"run_id": ["r"], "option_labels": ["A/B"]})
    out = vote_label_share(tokens, agents, runs)
    assert out.shows_own_vote.item() == 0.5  # agent 1 shows both labels
