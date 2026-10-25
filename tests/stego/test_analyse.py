import pandas as pd

from colx.stego.analyse import heard_after_counter, overlap_runs


def _tokens() -> pd.DataFrame:
    rows = []
    for run in ("bj__shoe00__collusion", "bj__shoe00__control"):
        for hand in (1, 2):
            for agent, toks in (("A", [1, 2]), ("B", [1, 3]), ("C", [4]), ("D", [5])):
                if run.endswith("control"):
                    toks = [10 + ord(agent)]
                rows += [
                    {
                        "run_id": run,
                        "hand": hand,
                        "agent": agent,
                        "layer": 23,
                        "token_id": t,
                        "rendering": "rel",
                        "position": "H-start",
                    }
                    for t in toks
                ]
    return pd.DataFrame(rows)


def test_overlap_runs_scores_the_shared_pair_per_run() -> None:
    out = overlap_runs(_tokens(), "rel").set_index("run_id")
    assert out.loc["bj__shoe00__collusion", "run_score"] == 1.0
    assert out.loc["bj__shoe00__collusion", "pair"] == ("A", "B")
    assert out.loc["bj__shoe00__control", "run_score"] == 0.0
    assert out.loc["bj__shoe00__collusion", "scenario_id"] == "shoe00"


def test_heard_after_counter_keeps_honest_calls_after_the_counter() -> None:
    calls = pd.DataFrame(
        {
            "run_id": ["r"] * 4,
            "hand": [1] * 4,
            "mode": ["collusion"] * 4,
            "agent": ["H1", "C", "H2", "B"],
            "role": ["honest", "counter", "honest", "big_player"],
        }
    )
    assert heard_after_counter(calls).agent.tolist() == ["H2"]
