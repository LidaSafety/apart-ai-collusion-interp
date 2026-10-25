import numpy as np
import pandas as pd

from colx.turns.classify import (
    heldout_scores,
    lens_model,
    own_messages,
    presence_matrix,
    scenario_folds,
)


def test_scenario_folds_keep_scenarios_together_and_are_seeded() -> None:
    scen = np.array(["a", "a", "b", "c", "c", "d"])
    folds = scenario_folds(scen, n_folds=2)
    assert folds[0] == folds[1] and folds[3] == folds[4]
    assert set(folds) == {0, 1}
    assert (folds == scenario_folds(scen, n_folds=2)).all()


def test_presence_matrix_rows_follow_keys() -> None:
    tokens = pd.DataFrame(
        {
            "run_id": ["r", "r", "r"],
            "agent": ["A", "B", "A"],
            "layer": [24, 24, 28],
            "token_id": [5, 5, 9],
        }
    )
    keys = pd.DataFrame({"run_id": ["r", "r"], "agent": ["B", "A"]})
    m = presence_matrix(tokens, keys).toarray()
    assert m.tolist() == [[1, 0], [1, 1]]  # columns (24, 5), (28, 9)


def test_heldout_scores_learn_a_clean_signal() -> None:
    rng = np.random.default_rng(0)
    y = np.array([0, 1] * 20)
    x = np.c_[y + rng.normal(0, 0.1, 40), rng.normal(0, 1, 40)]
    folds = np.arange(40) % 5
    scores = heldout_scores(x, y, folds, lens_model)
    assert scores[y == 1].min() > scores[y == 0].max()


def test_own_messages_take_the_first_rounds() -> None:
    msgs = ["[Ann]: one", "[Bo]: x", "[Ann]: two", "[Ann]: three"]
    assert own_messages(msgs, "Ann", 2) == "[Ann]: one\n[Ann]: two"
