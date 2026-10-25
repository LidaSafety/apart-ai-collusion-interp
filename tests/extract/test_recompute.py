import pytest
import torch
from torch import nn

from colx.extract.recompute import block_outputs, read_positions, token_containing

OFFSETS = [(0, 3), (3, 4), (4, 9), (9, 12)]


def test_token_containing() -> None:
    assert token_containing(OFFSETS, 0) == 0
    assert token_containing(OFFSETS, 3) == 1
    assert token_containing(OFFSETS, 8) == 2
    with pytest.raises(ValueError):
        token_containing(OFFSETS, 12)


def test_read_positions() -> None:
    rendered = "abcXhello.end"
    offsets = [(0, 3), (3, 4), (4, 10), (10, 13)]
    # discussion "hello." ends at char 9, inside token 2; P1 is the last token.
    assert read_positions(rendered, "hello.", offsets) == [3, 2]


def test_read_positions_needs_unique_discussion() -> None:
    with pytest.raises(ValueError):
        read_positions("hi hi", "hi", [(0, 2), (2, 5)])


class _Inner(nn.Module):
    """A 3-block stand-in for Qwen3's decoder stack."""

    def __init__(self) -> None:
        super().__init__()
        self.embed = nn.Embedding(10, 4)
        self.layers = nn.ModuleList([nn.Linear(4, 4) for _ in range(3)])

    def forward(self, input_ids: torch.Tensor, use_cache: bool = False) -> torch.Tensor:
        h = self.embed(input_ids)
        for layer in self.layers:
            h = layer(h)
        return h


class _Tiny(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.model = _Inner()

    @property
    def device(self) -> torch.device:
        return torch.device("cpu")


def test_block_outputs_are_each_blocks_output() -> None:
    torch.manual_seed(0)
    model = _Tiny()
    ids = [1, 2, 3, 4]
    out = block_outputs(model, ids, [3, 1])
    assert out.shape == (2, 3, 4)
    h = model.model.embed(torch.tensor([ids]))
    for i, layer in enumerate(model.model.layers):
        h = layer(h)
        torch.testing.assert_close(out[:, i], h[0, [3, 1]].detach())
