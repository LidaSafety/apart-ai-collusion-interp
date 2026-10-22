"""Load the pre-fitted Qwen3-32B J-lens and read residuals out through it.

Conventions (checked against the code that fitted the lens and the authors' library):
- layer l is the output of block l;
- readout = unembed(h @ J[l].T), with unembed = final RMSNorm then lm_head, in fp32.
"""

import hashlib
from pathlib import Path

import torch

from colx.unembed import Unembed

# 10 layers evenly spaced from 24 to 58: inside the paper's workspace band (~38-92% of the
# 63 lens layers; 24/63 = 38%, 58/63 = 92%).
LAYERS = (24, 28, 32, 35, 39, 43, 47, 50, 54, 58)


def sha256_of(path: Path, chunk: int = 1 << 24) -> str:
    """Return the file's sha256 hex digest."""
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def load_maps(path: Path, layers: tuple[int, ...] = LAYERS) -> dict[int, torch.Tensor]:
    """Load the J maps of `layers` from the lens file, as fp32 [d_model, d_model]."""
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    return {layer: checkpoint["J"][layer].float() for layer in layers}


def readout(residual: torch.Tensor, jmap: torch.Tensor, unembed: Unembed) -> torch.Tensor:
    """Lens logits of residuals [..., d_model] at one layer: unembed(h @ J.T), fp32."""
    h = residual.to(jmap.device, torch.float32)
    return unembed(h @ jmap.T)
