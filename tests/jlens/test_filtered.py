import pytest
import torch

from colx.jlens.filtered import is_word_token, relative_logprobs, view_scores


@pytest.mark.parametrize(
    ("text", "keep"),
    [
        (" audit", True),
        ("don't", True),
        ("继续保持", True),
        ("köln", True),
        ("7", True),
        (" **", False),
        ("…", False),
        ('."</', False),
        ("-ing", False),  # punctuation only allowed inside
        ("  ", False),
    ],
)
def test_is_word_token(text: str, keep: bool) -> None:
    assert is_word_token(text) is keep


def test_relative_logprobs_cancel_shared_content() -> None:
    # Token 0 is high for every agent; token 2 only for agent 1.
    logits = torch.tensor([[5.0, 0.0, 0.0], [5.0, 0.0, 3.0]])
    rel = relative_logprobs(logits)
    assert rel[1].argmax().item() == 2
    torch.testing.assert_close(rel.mean(0), torch.zeros(3))


def test_view_scores_words_keeps_raw_logits() -> None:
    logits = torch.randn(2, 4)
    assert torch.equal(view_scores(logits, "words"), logits)
