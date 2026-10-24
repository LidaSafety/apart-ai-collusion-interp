import pandas as pd

from colx.joint.inputs import INSTRUMENTS, run_rows


def test_run_rows_one_per_instrument_in_the_given_order() -> None:
    run = pd.Series({"run_id": "r", "brief": "brief", "discussion": "[Ann]: hi"})
    names = ["Bo", "Ann"]
    pooled = pd.Series({(n, p): f"{n}-{p}" for n in names for p in ("P1", "P2")})
    rows = pd.DataFrame(run_rows(run, names, pooled))
    assert list(zip(rows.arm, rows.position, strict=True)) == list(INSTRUMENTS)
    lens_p2 = rows[(rows.arm == "lens") & (rows.position == "P2")].prompt.item()
    assert "Agent 1: Bo-P2" in lens_p2 and "Agent 2: Ann-P2" in lens_p2
    assert all(order == names for order in rows.order)
