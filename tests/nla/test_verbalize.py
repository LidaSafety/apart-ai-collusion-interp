import torch

from colx.nla.verbalize import explanation, rescale


def test_explanation_takes_the_tagged_text_even_if_unclosed() -> None:
    assert explanation("<explanation> a bet is coming </explanation> extra") == "a bet is coming"
    assert explanation("noise <explanation>cut off here") == "cut off here"
    assert explanation("no tags") == "no tags"


def test_rescale_sets_the_row_norm() -> None:
    out = rescale(torch.tensor([[3.0, 4.0], [0.0, 2.0]]), 10.0)
    assert torch.allclose(out.norm(dim=-1), torch.tensor([10.0, 10.0]))
