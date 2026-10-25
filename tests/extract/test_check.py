import pandas as pd
import torch

from colx.extract.check import blocks_aligned, blocks_below, cosine_per_block, passed


def _residual_stack(n_blocks: int = 5, d: int = 16) -> torch.Tensor:
    """Blocks that drift: each is the previous plus a random step."""
    torch.manual_seed(0)
    return torch.cumsum(torch.randn(n_blocks, d), dim=0)


def test_cosine_per_block() -> None:
    stack = _residual_stack()
    torch.testing.assert_close(cosine_per_block(stack, stack), torch.ones(5))
    assert cosine_per_block(stack, -stack).max().item() < -0.99


def test_blocks_aligned_detects_shift() -> None:
    stack = _residual_stack()
    assert blocks_aligned(stack, stack + 0.01) == 5
    # Stored "block l" actually holding block l-1 (an off-by-one) breaks alignment.
    shifted = torch.cat([stack[:1], stack[:-1]])
    assert blocks_aligned(shifted, stack) < 5


def _table(**overrides: object) -> pd.DataFrame:
    row = {
        "p1_fresh": 9,
        "p1_stored": 9,
        "p2_fresh": 5,
        "p2_stored": 5,
        "ends_with_empty_think": True,
        "min_cos_p1": 0.9995,
        "min_cos_p2": 0.9999,
        "aligned_blocks_p1": 64,
        "aligned_blocks_p2": 64,
        "logit_lens_top1": 7,
        "first_reply_token": 7,
    }
    return pd.DataFrame([{**row, **overrides}])


def test_passed_all_true() -> None:
    assert all(passed(_table()).values())


def test_passed_flags_each_failure() -> None:
    assert not passed(_table(p2_stored=6))["p2_index_matches"]
    assert not passed(_table(min_cos_p2=0.998))["cosine_at_least_0.999"]
    assert not passed(_table(aligned_blocks_p1=63))["block_numbering_aligned"]
    assert not passed(_table(logit_lens_top1=8))["logit_lens_predicts_reply"]


def test_blocks_below() -> None:
    table = pd.DataFrame(
        [{"run_id": "r", "agent": "Ann", "cos_p1": [1.0, 0.998], "cos_p2": [0.9995, 1.0]}]
    )
    assert blocks_below(table) == {"r Ann P1": [1], "r Ann P2": []}
