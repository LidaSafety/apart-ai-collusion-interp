import math

import pandas as pd
import pytest
import torch

from colx.judge.run import format_check
from colx.judge.scoring import abc_scores, answer_probs, answer_token_ids, length_batches


class _Tok:
    def __init__(self) -> None:
        self.vocab = ["Yes", " yes", "NO", " No", "1", " 2", "3", "4", "maybe"]

    def __len__(self) -> int:
        return len(self.vocab)

    def decode(self, ids: list[int]) -> str:
        return "".join(self.vocab[i] for i in ids)


def test_answer_token_ids_collects_spellings() -> None:
    ids = answer_token_ids(_Tok())
    assert ids["yes"] == [0, 1]
    assert ids["no"] == [2, 3]
    assert ids["2"] == [5]


def test_answer_probs_sums_spellings() -> None:
    logits = torch.log(torch.tensor([[0.3, 0.2, 0.1, 0.1, 0.05, 0.05, 0.05, 0.05, 0.1]]))
    rec = answer_probs(logits, answer_token_ids(_Tok()))[0]
    assert rec["p_yes"] == pytest.approx(0.5)
    assert rec["p_no"] == pytest.approx(0.2)
    assert rec["top_token"] == 0


def test_abc_scores() -> None:
    s = abc_scores(0.9, 0.1)
    assert s["score_A"] == 0.9
    assert s["score_B"] == pytest.approx(0.9)
    assert s["score_C"] == pytest.approx(math.log(9))


def test_abc_scores_b_and_c_rank_alike() -> None:
    pairs = [(0.6, 0.3), (0.2, 0.05), (0.01, 0.5)]
    b = [abc_scores(*p)["score_B"] for p in pairs]
    c = [abc_scores(*p)["score_C"] for p in pairs]
    assert sorted(range(3), key=b.__getitem__) == sorted(range(3), key=c.__getitem__)


def test_length_batches_respects_budget() -> None:
    batches = length_batches([10, 50, 20, 40], max_tokens=80)
    assert sorted(i for b in batches for i in b) == [0, 1, 2, 3]
    lengths = [10, 50, 20, 40]
    assert all(max(lengths[i] for i in b) * len(b) <= 80 for b in batches)


def test_format_check() -> None:
    scores = pd.DataFrame(
        [
            {"kind": "yesno", "p_yes": 0.7, "p_no": 0.2, "top_token_text": "Yes",
             "p_1": 0, "p_2": 0, "p_3": 0, "p_4": 0},
            {"kind": "yesno", "p_yes": 0.1, "p_no": 0.2, "top_token_text": "I",
             "p_1": 0, "p_2": 0, "p_3": 0, "p_4": 0},
            {"kind": "number", "p_yes": 0, "p_no": 0, "top_token_text": "3",
             "p_1": 0.1, "p_2": 0.1, "p_3": 0.7, "p_4": 0.1},
        ]
    )  # fmt: skip
    checks = format_check(scores)
    assert checks["top token is Yes/No"] == 1
    assert checks["P(Yes)+P(No) >= 0.5"] == 1
    assert checks["top token is 1-4"] == 1
