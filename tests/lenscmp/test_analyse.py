import pandas as pd

from colx.lenscmp.analyse import f1_scores


def test_f1_scores_one_row_per_run_with_labels() -> None:
    rows = []
    for run, shared in (("a__s1__collusion", True), ("a__s1__control", False)):
        for agent, toks in (
            ("A", [1, 2]),
            ("B", [1, 2] if shared else [3]),
            ("C", [4]),
            ("D", [5]),
        ):
            rows += [
                {
                    "run_id": run,
                    "agent": agent,
                    "position": "P1",
                    "layer": 13,
                    "token_id": t,
                    "rendering": "rel",
                }
                for t in toks
            ]
    runs = pd.DataFrame(
        {
            "run_id": ["a__s1__collusion", "a__s1__control"],
            "scenario_id": ["s1", "s1"],
            "mode": ["collusion", "control"],
            "style_group": ["g", "g"],
            "colluded": [True, False],
        }
    )
    out = f1_scores(pd.DataFrame(rows), runs, "rel").set_index("run_id")
    assert out.loc["a__s1__collusion", "run_score"] == 2.0
    assert out.loc["a__s1__control", "run_score"] == 0.0
