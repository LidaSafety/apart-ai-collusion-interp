import pytest
import torch

from colx.jlens.render import (
    is_printable_token,
    printable_mask,
    render_grid,
    show_token,
    top_tokens,
)


class _FakeTokenizer:
    """Five tokens: a word, a byte fragment, a newline, a sub-word piece, a special token."""

    def __init__(self) -> None:
        self.vocab = [" audit", "�", "\n", "ing", "<|im_end|>"]
        self.all_special_ids = [4]
        self.added_tokens_decoder = {4: "<|im_end|>"}

    def __len__(self) -> int:
        return len(self.vocab)

    def decode(self, ids: list[int]) -> str:
        return "".join(self.vocab[i] for i in ids)


@pytest.mark.parametrize(
    ("text", "keep"),
    [(" audit", True), ("ing", True), (",", True), ("�", False), ("\n", False), ("  ", False)],
)
def test_is_printable_token(text: str, keep: bool) -> None:
    assert is_printable_token(text) is keep


def test_printable_mask_drops_fragments_and_specials() -> None:
    mask = printable_mask(_FakeTokenizer(), vocab_size=6)
    assert mask.tolist() == [True, False, False, True, False, False]


def test_top_tokens_filters_before_taking_top_k() -> None:
    logits = torch.tensor([[1.0, 9.0, 8.0, 2.0, 7.0, 0.0]])
    mask = torch.tensor([True, False, False, True, False, False])
    # The three highest logits are all masked; the top 2 printable are 3 then 0.
    assert top_tokens(logits, mask, k=2).tolist() == [[3, 0]]


def test_show_token_marks_leading_spaces() -> None:
    assert show_token(" audit") == "␣audit"
    assert show_token("  x") == "␣␣x"
    assert show_token("ing") == "ing"


def test_render_grid_one_line_per_layer_in_order() -> None:
    grid = render_grid({28: ["b"], 24: [" a", "c"]})
    assert grid == "Layer 24: ␣a | c\nLayer 28: b"
