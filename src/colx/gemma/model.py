"""Load Gemma-3-27B-IT, render its chat prompts, and unembed residuals (plan: gemma.md).

- Gemma 3 has no system role: the chat template puts the system text at the start of the
  first user turn, then a blank line. We render each call as NARCBench sent it (system +
  user) with the model's own template, so the tokens match what vLLM generated from.
- Gemma 3 loads as a multimodal model; its text decoder is `model.model.language_model`
  (the layout the pinned jacobian-lens library also uses), the unembedding is `lm_head`.
- Unembed = the model's own final norm (Gemma's RMSNorm scales by 1 + weight), then
  lm_head, in fp32, then the logit soft cap if the config has one.
"""

import copy
from pathlib import Path

import torch
from transformers import AutoModelForImageTextToText, AutoTokenizer

MODEL_ID = "google/gemma-3-27b-it"
MODEL_REVISION = "005ad3404e59d6023443cb575daa05336842228a"
LENS_SHA256 = "53f528a96a763c9146d441baa3059b4556b02af1b94b1a870200447b4ae809d9"
LENS_REVISION = "e166deb5ad540932100ef803c8c9bcc2a5453694"
# 10 layers evenly spaced over 38-92% of depth (0-61), as Qwen's 24..58 of 63.
LAYERS = (23, 27, 30, 34, 38, 41, 45, 49, 52, 56)


def load(model_dir: Path):
    """Tokenizer and bf16 model on the GPU, in eval mode."""
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModelForImageTextToText.from_pretrained(
        model_dir, dtype=torch.bfloat16, device_map="cuda"
    )
    return tokenizer, model.eval()


def decoder_layers(model) -> torch.nn.ModuleList:
    """The text decoder's blocks; layer l = the output of block l."""
    return model.model.language_model.layers


def render(tokenizer, system: str, user: str) -> str:
    """One call as NARCBench sent it, rendered by Gemma's own chat template."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)


class Unembed:
    """fp32 copy of the final norm and lm_head, plus the config's logit soft cap."""

    def __init__(self, model) -> None:
        self.norm = copy.deepcopy(model.model.language_model.norm).float()
        self.weight = model.lm_head.weight.detach().float()
        self.softcap = getattr(model.config.get_text_config(), "final_logit_softcapping", None)

    def __call__(self, residual: torch.Tensor) -> torch.Tensor:
        """Map residuals [..., d] to fp32 logits [..., vocab]."""
        logits = self.norm(residual.to(self.weight.device, torch.float32)) @ self.weight.T
        if self.softcap is not None:
            logits = self.softcap * torch.tanh(logits / self.softcap)
        return logits
