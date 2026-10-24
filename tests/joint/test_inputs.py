import pandas as pd

from colx.joint.inputs import INSTRUMENTS, run_rows


def test_instruments_are_the_nine_of_the_plan() -> None:
    assert len(INSTRUMENTS) == 9 and ("lens_rel", "P1") in INSTRUMENTS


def test_run_rows_one_per_instrument_with_the_right_lens_text() -> None:
    run = pd.Series({"run_id": "r", "brief": "brief", "discussion": "[Ann]: hi"})
    names = ["Bo", "Ann"]
    lens = pd.Series(
        {
            (r, n, p): f"{r}-{n}-{p}"
            for r in ("raw", "rel", "pooled")
            for n in names
            for p in ("P1", "P2")
        }
    )
    rows = pd.DataFrame(run_rows(run, names, lens))
    assert list(zip(rows.arm, rows.position, strict=True)) == list(INSTRUMENTS)
    pick = rows.set_index(["arm", "position"]).prompt
    assert "Agent 1: pooled-Bo-P2" in pick[("lens_pooled", "P2")]
    assert "Agent 2:\nraw-Ann-P1" in pick[("lens_raw", "P1")]
    assert "Agent 1 (Bo):\nrel-Bo-P2" in pick[("both", "P2")]
    assert all(order == names for order in rows.order)
