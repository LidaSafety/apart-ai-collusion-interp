import numpy as np
import pandas as pd

from colx.app.data import instrument_name, mistakes, roc_points


def test_instrument_name() -> None:
    assert instrument_name("lens", "rel", "P2") == "Lens judge · words-relative · P2"
    assert instrument_name("text", "-", "-") == "Text baseline"


def test_roc_points_endpoints_and_perfect_curve() -> None:
    roc = roc_points(np.array([0.9, 0.8, 0.2, 0.1]), np.array([1, 1, 0, 0]))
    assert roc.iloc[0].tolist() == [0.0, 0.0] and roc.iloc[-1].tolist() == [1.0, 1.0]
    assert ((roc.fpr == 0) & (roc.tpr == 1)).any()


def test_mistakes() -> None:
    runs = pd.DataFrame({"run_id": list("abcd"), "run_score": [0.9, 0.1, 0.8, 0.2],
                         "run_colluded": [False, True, True, False]})  # fmt: skip
    out = mistakes(runs, k=1)
    assert out.set_index("kind").run_id.to_dict() == {"false alarm": "a", "miss": "b"}
