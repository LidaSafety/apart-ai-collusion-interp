import pandas as pd

from colx.judge import prompts
from colx.judge.inputs import lens_rows, name_orders, text_rows


def _agents(mode: str = "collusion") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "run_id": ["r"] * 4,
            "agent_index": [0, 1, 2, 3],
            "agent": ["Ann", "Bo", "Cy", "Di"],
            "mode": [mode] * 4,
            "system_prompt": ["You are X."] * 4,
            "vote_line": ["RECOMMENDATION: Option A"] * 4,
        }
    )


def _grid() -> dict:
    keys = [("r", i, p) for i in range(4) for p in ("P1", "P2")]
    return {
        arm: pd.Series({k: f"Layer 24: {arm}{k[1]}{k[2]}" for k in keys}) for arm in ("raw", "rel")
    }


def test_name_orders_seeded_and_complete() -> None:
    a = name_orders(_agents())
    assert sorted(a["r"]) == ["Ann", "Bo", "Cy", "Di"]
    assert a == name_orders(_agents())


def test_lens_rows_counts_and_answers() -> None:
    rows = pd.DataFrame(lens_rows(_agents(), pd.Series({"r": "brief"}), _grid()))
    counts = rows.groupby("judge").size().to_dict()
    # 4 agents x 2 arms x 2 positions; name control P1 only.
    assert counts == {"lens": 16, "instruction_control": 16, "name_control": 8}
    name = rows[rows.judge == "name_control"].iloc[0]
    order = name_orders(_agents())["r"]
    assert name.true_number == order.index(name.agent) + 1
    lens = rows[(rows.judge == "lens") & (rows.arm == "rel") & (rows.position == "P2")].iloc[0]
    assert "rel0P2" in lens.prompt and prompts.COLLUSION_Q in lens.prompt


def test_control_runs_get_no_instruction_control() -> None:
    rows = pd.DataFrame(lens_rows(_agents("control"), pd.Series({"r": "brief"}), _grid()))
    assert "instruction_control" not in set(rows.judge)


def test_text_rows_name_the_agent() -> None:
    runs = pd.DataFrame({"brief": ["b"], "discussion": ["[Ann]: hi"]}, index=["r"])
    rows = pd.DataFrame(text_rows(_agents(), runs, {"r": "[Ann]: secret"}))
    assert set(rows.judge) == {"judge_works", "text", "instruction_only", "vote"}
    works = rows[(rows.judge == "judge_works") & (rows.agent == "Bo")].prompt.item()
    assert "Was Bo told to collude?" in works and "[Ann]: secret" in works
    text = rows[(rows.judge == "text") & (rows.agent == "Cy")].prompt.item()
    assert "Is Cy about to vote" in text
