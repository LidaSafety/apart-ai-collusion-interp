"""The model's unembedding (final RMSNorm, then lm_head), computed in fp32.

Both the logit-lens check and the J-lens readout map a residual to vocabulary logits this
way. Doing it in fp32 (the plan's choice) keeps near-tied tokens in a stable order. The
weights can come from a loaded model or straight from the checkpoint files, so applying the
lens to stored activations needs no GPU.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import torch
from safetensors import safe_open

NORM_KEY = "model.norm.weight"
LM_HEAD_KEY = "lm_head.weight"


@dataclass(frozen=True)
class Unembed:
    """Final RMSNorm weight and epsilon, and the lm_head matrix, all fp32."""

    norm_weight: torch.Tensor
    eps: float
    lm_head: torch.Tensor

    def __call__(self, residual: torch.Tensor) -> torch.Tensor:
        """Map residuals [..., d_model] to fp32 logits [..., vocab]."""
        h = residual.to(self.lm_head.device, torch.float32)
        h = h * torch.rsqrt(h.pow(2).mean(-1, keepdim=True) + self.eps)
        return (self.norm_weight * h) @ self.lm_head.T


def from_model(model: torch.nn.Module) -> Unembed:
    """Take the unembedding from a loaded Qwen3 causal LM."""
    norm = model.model.norm
    return Unembed(
        norm_weight=norm.weight.detach().float(),
        eps=float(norm.variance_epsilon),
        lm_head=model.lm_head.weight.detach().float(),
    )


def from_checkpoint(model_dir: Path, device: str = "cpu") -> Unembed:
    """Read the unembedding weights from a local Qwen3 checkpoint folder."""
    index = json.loads((model_dir / "model.safetensors.index.json").read_text())["weight_map"]
    tensors = {}
    for key in (NORM_KEY, LM_HEAD_KEY):
        with safe_open(str(model_dir / index[key]), "pt", device=device) as f:
            tensors[key] = f.get_tensor(key).float()
    config = json.loads((model_dir / "config.json").read_text())
    return Unembed(
        norm_weight=tensors[NORM_KEY],
        eps=float(config["rms_norm_eps"]),
        lm_head=tensors[LM_HEAD_KEY],
    )
