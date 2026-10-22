"""Load Qwen3-32B and render its chat prompts the way the transcripts were generated.

Generation used vLLM chat (system + user) with thinking disabled. With
`enable_thinking=False`, Qwen3's chat template ends the prompt with an empty
`<think>\\n\\n</think>\\n\\n` block, so the last prompt token (P1) is the "\\n\\n" after it.
"""

from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from transformers import AutoModelForCausalLM, AutoTokenizer, PreTrainedTokenizerBase

from colx.provenance import MODEL_ID, MODEL_REVISION

EMPTY_THINK = "<think>\n\n</think>\n\n"


def _revision(model_path: str) -> str | None:
    """Pin the Hub revision when loading by id; a local path is already one snapshot."""
    return MODEL_REVISION if model_path == MODEL_ID else None


def load_tokenizer(model_path: str = MODEL_ID) -> PreTrainedTokenizerBase:
    """Load the Qwen3 tokenizer."""
    return AutoTokenizer.from_pretrained(model_path, revision=_revision(model_path))


def load_model(model_path: str = MODEL_ID) -> torch.nn.Module:
    """Load Qwen3-32B in bf16 on the GPU, in eval mode (needs an 80 GB GPU)."""
    model = AutoModelForCausalLM.from_pretrained(
        model_path, revision=_revision(model_path), dtype=torch.bfloat16, device_map="cuda"
    )
    return model.eval()


def render_chat(tokenizer: PreTrainedTokenizerBase, system: str | None, user: str) -> str:
    """Render one chat turn as text, ending at the assistant's (empty-think) header."""
    messages = [{"role": "system", "content": system}] if system is not None else []
    messages.append({"role": "user", "content": user})
    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True, enable_thinking=False
    )


def local_dir(model_path: str) -> Path:
    """Return a local snapshot folder: the path itself, or the Hub snapshot of the pinned id."""
    if Path(model_path).is_dir():
        return Path(model_path)
    return Path(snapshot_download(model_path, revision=_revision(model_path)))
