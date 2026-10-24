"""Read every discussion turn through the J-lens: raw and words-relative top-25 tokens.

As round 4 (`colx.jlens.tokens`, `colx.jlens.filtered`):
- raw: the top 25 printable tokens by lens logit;
- words-relative: the lens log-probabilities minus their mean over the 400 calls of the
  same round (same position and layer), then the top 25 word tokens.
Output: one row per (call, position, layer, rank) with the token id and text.
"""

import pandas as pd
import torch

from colx.jlens.filtered import relative_logprobs, word_mask
from colx.jlens.lens import LAYERS, readout
from colx.jlens.render import printable_mask, top_tokens
from colx.turns.stored import TURN_POSITIONS
from colx.unembed import Unembed

RENDERINGS = ("raw", "rel")


def layer_ids(logits: torch.Tensor, rounds: torch.Tensor, masks: dict) -> dict[str, torch.Tensor]:
    """Top-25 ids per call for both renderings; relative within each round: two [n, 25]."""
    rel = torch.empty_like(logits)
    for r in rounds.unique():
        rows = rounds == r
        rel[rows] = relative_logprobs(logits[rows])
    return {"raw": top_tokens(logits, masks["raw"]), "rel": top_tokens(rel, masks["rel"])}


def token_table(
    index: pd.DataFrame, resid: torch.Tensor, maps: dict, unembed: Unembed, tokenizer, log=print
) -> pd.DataFrame:
    """Long table of both renderings' top-25 tokens for every call, position and layer."""
    vocab = unembed.lm_head.shape[0]
    masks = {"raw": printable_mask(tokenizer, vocab), "rel": word_mask(tokenizer, vocab)}
    rounds = torch.as_tensor(index["round"].to_numpy())
    texts: dict[int, str] = {}
    frames = []
    for li, layer in enumerate(LAYERS):
        for p, position in enumerate(TURN_POSITIONS):
            logits = readout(resid[:, p, li], maps[layer], unembed)
            for rendering, ids in layer_ids(logits, rounds.to(logits.device), masks).items():
                ids = ids.cpu().numpy()
                frame = index[["run_id", "agent", "round"]].loc[index.index.repeat(ids.shape[1])]
                frames.append(
                    frame.assign(
                        position=position,
                        layer=layer,
                        rendering=rendering,
                        rank=list(range(ids.shape[1])) * len(index),
                        token_id=ids.reshape(-1),
                    )
                )
        log(f"layer {layer} done")
    table = pd.concat(frames, ignore_index=True)
    for token_id in table["token_id"].unique():
        texts[int(token_id)] = tokenizer.decode([int(token_id)])
    return table.assign(token=table["token_id"].map(texts))
