"""Recompute round-4 residuals from the transcripts, to check the stored ones.

Layer convention (same as the lens): block l's residual is the output of
`model.model.layers[l]`, read with a forward hook.
"""

import torch
from transformers import PreTrainedTokenizerBase


def token_containing(offsets: list[tuple[int, int]], char_index: int) -> int:
    """Return the index of the token whose character span covers `char_index`."""
    for i, (start, end) in enumerate(offsets):
        if start <= char_index < end:
            return i
    raise ValueError(f"no token covers character {char_index}")


def read_positions(rendered: str, discussion: str, offsets: list[tuple[int, int]]) -> list[int]:
    """Return the token indices of P1 (last prompt token) and P2 (end of the discussion)."""
    if rendered.count(discussion) != 1:
        raise ValueError("the discussion must appear exactly once in the prompt")
    last_char = rendered.index(discussion) + len(discussion) - 1
    return [len(offsets) - 1, token_containing(offsets, last_char)]


def tokenize_with_offsets(
    tokenizer: PreTrainedTokenizerBase, rendered: str
) -> tuple[list[int], list[tuple[int, int]]]:
    """Tokenize a rendered chat prompt (it already holds its special tokens)."""
    encoded = tokenizer(rendered, add_special_tokens=False, return_offsets_mapping=True)
    return encoded["input_ids"], [tuple(o) for o in encoded["offset_mapping"]]


@torch.inference_mode()
def block_outputs(
    model: torch.nn.Module, input_ids: list[int], positions: list[int]
) -> torch.Tensor:
    """Run one forward pass; return every block's output at `positions`: [pos, blocks, d]."""
    layers = model.model.layers
    captured: dict[int, torch.Tensor] = {}

    def hook_for(index: int):
        def hook(_module, _inputs, output) -> None:
            hidden = output if torch.is_tensor(output) else output[0]
            captured[index] = hidden[0, positions].detach().cpu()

        return hook

    handles = [layer.register_forward_hook(hook_for(i)) for i, layer in enumerate(layers)]
    try:
        ids = torch.tensor([input_ids], device=model.device)
        model.model(input_ids=ids, use_cache=False)
    finally:
        for handle in handles:
            handle.remove()
    return torch.stack([captured[i] for i in range(len(layers))], dim=1)
