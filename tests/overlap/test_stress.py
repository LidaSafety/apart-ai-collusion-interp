import pandas as pd

from colx.overlap.stress import operating_point


def table(mode: str, scores: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {"instrument": "lens_raw", "mode": mode, "run_score": scores, "scenario_id": "s"}
    )


def test_operating_point_uses_the_core_controls() -> None:
    core = pd.concat([table("control", [0, 1, 2, 3]), table("collusion", [5, 6, 2.5, 1])])
    out = operating_point(core, {"aware": table("collusion", [4, 0])})
    assert out["thresholds"]["zero_of_50"] == 3
    assert out["core"]["zero_of_50"] == 0.5 and out["aware"]["zero_of_50"] == 0.5
