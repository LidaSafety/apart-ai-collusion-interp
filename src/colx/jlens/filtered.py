"""Exploratory filtered lens readouts: words only, and words with common content removed.

Two alternative renderings of the same stored P1/P2 residuals (the planned raw readout is
left untouched):
- **words**: the top 25 among tokens that decode to a word (letters or digits, with an
  internal apostrophe, hyphen or right single quote allowed), the rule of the authors'
  display mask (`jlens/vis.py`, `_meaningful_token_mask`); punctuation and markup are
  dropped before the top 25.
- **words_relative**: the agent's lens log-probabilities minus their mean over all 400
  agents at that position and layer, then the words-only top 25. What every agent shows at
  that layer (formatting, filler, the coming request) cancels out.
"""

from pathlib import Path

import pandas as pd
import torch
from safetensors.torch import load_file

from colx import provenance, qwen
from colx.jlens.lens import LAYERS, load_maps, readout
from colx.jlens.render import printable_mask, top_tokens
from colx.jlens.tokens import POSITIONS, token_rows
from colx.unembed import from_checkpoint

VIEWS = ("words", "words_relative")
INNER_PUNCT = "'-\u2019"  # apostrophe, hyphen, right single quote


def is_word_token(text: str) -> bool:
    """True if the stripped token is letters/digits, with inner apostrophes or hyphens allowed."""
    s = text.strip()
    return bool(s) and all(
        ch.isalnum() or (0 < i < len(s) - 1 and ch in INNER_PUNCT) for i, ch in enumerate(s)
    )


def word_mask(tokenizer, vocab_size: int) -> torch.Tensor:
    """Printable, non-special tokens that are also word tokens: [vocab_size] bool."""
    mask = printable_mask(tokenizer, vocab_size)
    for token_id in mask.nonzero().flatten().tolist():
        mask[token_id] = is_word_token(tokenizer.decode([token_id]))
    return mask


def relative_logprobs(logits: torch.Tensor) -> torch.Tensor:
    """Log-probabilities minus their mean over rows (agents): [n, vocab] → [n, vocab]."""
    logp = torch.log_softmax(logits, dim=-1)
    return logp - logp.mean(dim=0, keepdim=True)


def view_scores(logits: torch.Tensor, view: str) -> torch.Tensor:
    """The scores ranked for a view: raw logits for words, relative log-probs otherwise."""
    return logits if view == "words" else relative_logprobs(logits)


def compute_views(model_dir: Path, lens_path: Path, out_dir: Path, device: str) -> dict:
    """Token tables for both views, all agents, P1/P2, the 10 plan layers."""
    index = pd.read_parquet(out_dir / "activations_index.parquet")
    resid = load_file(str(out_dir / "activations.safetensors"))["resid"]
    tokenizer = qwen.load_tokenizer(str(model_dir))
    unembed = from_checkpoint(model_dir, device=device)
    mask = word_mask(tokenizer, unembed.lm_head.shape[0])
    maps = load_maps(lens_path)
    decode = lambda token_id: tokenizer.decode([token_id])  # noqa: E731 (tiny local alias)
    rows: dict[str, list] = {view: [] for view in VIEWS}
    for layer in LAYERS:
        jmap = maps[layer].to(device)
        for p, position in enumerate(POSITIONS):
            logits = readout(resid[:, p, layer], jmap, unembed)
            for view in VIEWS:
                scores = view_scores(logits, view)
                ids = top_tokens(scores, mask)
                vals = scores.gather(-1, ids)
                rows[view] += token_rows(index, position, layer, ids.cpu(), vals.cpu(), decode)
    return {view: pd.DataFrame(r).rename(columns={"prob": "score"}) for view, r in rows.items()}


def write_views(model_dir: Path, lens_path: Path, out_dir: Path, device: str) -> dict:
    """Save `filtered/lens_tokens_<view>.parquet` (exploratory) next to the raw readout."""
    tables = compute_views(model_dir, lens_path, out_dir, device)
    folder = out_dir / "filtered"
    folder.mkdir(parents=True, exist_ok=True)
    meta = provenance.collect("col lens-judge lens-tokens-filtered", label="exploratory")
    for view, table in tables.items():
        path = folder / f"lens_tokens_{view}.parquet"
        table.to_parquet(path, index=False)
        provenance.write_meta(path, meta | {"view": view})
    return {view: len(table) for view, table in tables.items()}
