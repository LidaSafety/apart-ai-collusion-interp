"""Turn lens logits into the judge's view: the top-25 printable tokens per layer.

Rendering rule (plan, after the paper's Fig. 40): decode each token id on its own; drop
tokens that don't decode to printable text (byte fragments, whitespace-only and control
tokens, special tokens); *then* take the top 25, so every line has exactly 25 tokens. A
leading space shows as "␣"; sub-word pieces are kept as they are.
"""

import torch
from transformers import PreTrainedTokenizerBase

TOP_K = 25
SPACE_MARK = "␣"
SEPARATOR = " | "


def is_printable_token(text: str) -> bool:
    """True if a decoded token is printable text (not a byte fragment or whitespace)."""
    return bool(text.strip()) and "�" not in text and text.isprintable()


def printable_mask(tokenizer: PreTrainedTokenizerBase, vocab_size: int) -> torch.Tensor:
    """Vocabulary mask [vocab_size]: True for ids that decode to printable, non-special text."""
    special = set(tokenizer.all_special_ids) | set(tokenizer.added_tokens_decoder)
    mask = torch.zeros(vocab_size, dtype=torch.bool)
    for token_id in range(min(vocab_size, len(tokenizer))):
        if token_id not in special:
            mask[token_id] = is_printable_token(tokenizer.decode([token_id]))
    return mask


def top_tokens(logits: torch.Tensor, mask: torch.Tensor, k: int = TOP_K) -> torch.Tensor:
    """Ids of the k highest-logit printable tokens, best first: [..., k]."""
    masked = logits.masked_fill(~mask.to(logits.device), float("-inf"))
    return masked.topk(k, dim=-1).indices


def show_token(text: str) -> str:
    """Display form of a decoded token: each leading space becomes "␣"."""
    stripped = text.lstrip(" ")
    return SPACE_MARK * (len(text) - len(stripped)) + stripped


def render_grid(lines: dict[int, list[str]]) -> str:
    """One line per layer: "Layer 24: ␣tok | piece | …" with the displayed tokens."""
    return "\n".join(
        f"Layer {layer}: " + SEPARATOR.join(show_token(t) for t in tokens)
        for layer, tokens in sorted(lines.items())
    )
