import pandas as pd

from colx.gemma.gate import gate


def _tables(n_colluded: int, n_not: int, unparsed: bool = False):
    runs = pd.DataFrame(
        {
            "mode": ["collusion"] * (n_colluded + n_not) + ["control"] * 5,
            "colluded": [True] * n_colluded + [False] * (n_not + 5),
        }
    )
    agents = pd.DataFrame(
        {
            "role": ["colluder"] * 2 * (n_colluded + n_not),
            "voted_target": [True] * 2 * n_colluded + [False] * 2 * n_not,
            "vote": ["A"] * 2 * (n_colluded + n_not),
        }
    )
    if unparsed:
        agents.loc[0, "vote"] = "?"
    return agents, runs


def test_gate_passes_with_enough_of_each_group() -> None:
    assert gate(*_tables(20, 12), errors=0)["passes"]


def test_gate_fails_on_too_few_non_colluding_runs_errors_or_unparsed_votes() -> None:
    assert not gate(*_tables(20, 5), errors=0)["passes"]
    assert not gate(*_tables(20, 12), errors=1)["passes"]
    assert not gate(*_tables(20, 12, unparsed=True), errors=0)["passes"]
