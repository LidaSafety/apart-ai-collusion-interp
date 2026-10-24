import pytest
import torch

from colx.joint.scoring import digit_token_ids, parse_pair, rating_records


class _Tok:
    def __init__(self) -> None:
        self.vocab = ["0", " 0", "3", "9", "10", "maybe"]

    def __len__(self) -> int:
        return len(self.vocab)

    def decode(self, ids: list[int]) -> str:
        return "".join(self.vocab[i] for i in ids)


def test_digit_token_ids_collect_spellings_but_not_multi_digit() -> None:
    ids = digit_token_ids(_Tok())
    assert ids["0"] == [0, 1]
    assert ids["9"] == [3]
    assert all(4 not in v for v in ids.values())


def test_expected_rating_normalises_over_digits() -> None:
    # P(0) = 0.2 (two spellings), P(3) = 0.1, P(9) = 0.1; the rest is not a digit.
    probs = torch.tensor([[0.1, 0.1, 0.1, 0.1, 0.3, 0.3]])
    rec = rating_records(torch.log(probs), digit_token_ids(_Tok()))[0]
    assert rec["digit_mass"] == pytest.approx(0.4)
    assert rec["rating"] == pytest.approx((3 * 0.1 + 9 * 0.1) / 0.4)
    assert rec["top_digit"] == 0
    assert rec["top_token"] == 4


@pytest.mark.parametrize(
    ("text", "pair"),
    [
        ("7\nPAIR: 3 and 1\nThey both ...", (1, 3)),
        ("2\nPair: Agent 2 and Agent 4", (2, 4)),
        ("5\nPAIR: 1, 2", (1, 2)),
        ("1\nPAIR: none", None),
        ("4\nPAIR: 2 and 2", None),
        ("6\nno pair line", None),
    ],
)
def test_parse_pair(text: str, pair: tuple[int, int] | None) -> None:
    assert parse_pair(text) == pair
