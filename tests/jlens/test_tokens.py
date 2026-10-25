import pandas as pd
import torch

from colx.jlens.tokens import grids, layer_top_tokens, token_rows
from colx.unembed import Unembed


def test_layer_top_tokens_shapes_and_probabilities() -> None:
    torch.manual_seed(0)
    unembed = Unembed(norm_weight=torch.ones(4), eps=1e-6, lm_head=torch.randn(30, 4))
    mask = torch.ones(30, dtype=torch.bool)
    ids, probs = layer_top_tokens(torch.randn(3, 4), torch.eye(4), unembed, mask)
    assert ids.shape == probs.shape == (3, 25)
    assert (probs[:, :-1] >= probs[:, 1:]).all()  # ranked by lens probability
    assert probs.sum(-1).max() <= 1.0 + 1e-6


def test_token_rows_and_grids() -> None:
    index = pd.DataFrame({"run_id": ["r"], "agent_index": [0], "agent": ["Ann"]})
    ids, probs = torch.tensor([[2, 1]]), torch.tensor([[0.5, 0.2]])
    rows = token_rows(index, "P1", 24, ids, probs, decode=lambda i: [" x", "y", " z"][i])
    rows += token_rows(index, "P1", 28, ids, probs, decode=lambda i: ["a", "b", "c"][i])
    table = pd.DataFrame(rows)
    assert table["rank"].tolist() == [0, 1, 0, 1]
    grid = grids(table).loc[0, "grid"]
    assert grid == "Layer 24: ␣z | y\nLayer 28: c | b"
