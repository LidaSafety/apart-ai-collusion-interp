import pandas as pd

from colx.stego.roc import pit_boss_point, shoe


def test_shoe_reads_the_shoe_from_a_run_id() -> None:
    assert shoe("bj__shoe08__collusion") == "shoe08"


def test_pit_boss_point_is_false_and_true_positive_rate_of_the_flag() -> None:
    flags = pd.DataFrame(
        {
            "mode": ["collusion", "collusion", "control", "control"],
            "flagged": [True, False, False, False],
        }
    )
    assert pit_boss_point(flags) == (0.0, 0.5)


def test_a_flag_that_never_fires_sits_at_the_origin() -> None:
    flags = pd.DataFrame({"mode": ["collusion", "control"], "flagged": [False, False]})
    assert pit_boss_point(flags) == (0.0, 0.0)
