import numpy as np
import pandas as pd

from colx.turns.classify import presence_matrix
from colx.turns.followup import by_followers, top_features


def _colluders() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "run_id": ["r1", "r1", "r2", "r2"],
            "agent": ["A", "B", "C", "D"],
            "voted_target": [True, True, False, True],
        }
    )


def test_by_followers_groups_runs_by_count() -> None:
    assert by_followers(_colluders(), np.array([0.8, 0.6, 0.2, 0.4])) == {1: 0.3, 2: 0.7}


def test_top_features_point_toward_the_label() -> None:
    c = _colluders()
    here = pd.DataFrame(
        {
            "run_id": ["r1", "r1", "r2", "r2"],
            "agent": ["A", "B", "D", "C"],
            "layer": [24, 24, 24, 24],
            "token_id": [1, 1, 1, 2],
            "token": ["go", "go", "go", "stop"],
        }
    )
    out = top_features(presence_matrix(here, c), here, c, k=1)
    assert out.iloc[0].token == "go" and out.iloc[0].followers == 3
    assert out.iloc[1].token == "stop" and out.iloc[1].non_followers == 1
