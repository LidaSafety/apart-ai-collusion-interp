import pandas as pd

from colx.nla.analyse import e1, e3
from colx.nla.judge import e1_prompt, e2_prompt


def test_e1_prompt_holds_the_description_and_asks_for_a_digit() -> None:
    text = e1_prompt("thinks the deck is rich in tens")
    assert "rich in tens" in text and text.endswith("(no formatting).")


def test_e2_prompt_numbers_the_agents() -> None:
    text = e2_prompt("brief", ["plans a vote", "worries"])
    assert "Agent 1: plans a vote" in text and "Agent 2: worries" in text and "PAIR:" in text


def _table() -> pd.DataFrame:
    rows = []
    for s in range(6):
        run = f"bj__shoe{s:02d}__collusion"
        for hand, label in ((1, "HOT"), (2, "NEGATIVE")):
            hot = label == "HOT"
            rows += [
                {
                    "run_id": run,
                    "hand": hand,
                    "label": label,
                    "role": "big_player",
                    "rating": 8.0 if hot else 1.0,
                    "description": "big bet coming" if hot else "calm",
                },
                {
                    "run_id": run,
                    "hand": hand,
                    "label": label,
                    "role": "honest",
                    "rating": 4.0,
                    "description": "chatting",
                },
            ]
    return pd.DataFrame(rows)


def test_e1_big_player_separates_hot_hands_honest_does_not() -> None:
    out = e1(_table(), leaky=set(), n_boot=50)
    assert out["big_player"]["auroc"] == 1.0 and out["honest_after_counter"]["auroc"] == 0.5
    assert out["difference"]["diff"] == 0.5


def test_e3_lists_words_over_represented_for_the_big_player() -> None:
    assert "big" in e3(_table())["big_player"]
