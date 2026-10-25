"""The two models of the series behind one interface (stego extraction and readout).

| | Gemma-3-27B-IT | Qwen3-32B |
|---|---|---|
| load | `colx.gemma.model.load` (multimodal class) | `colx.qwen` (causal LM) |
| prompt | Gemma's template (system folded into the user turn) | Qwen's template, thinking off |
| blocks | `model.model.language_model.layers` | `model.model.layers` |
| unembed | model's own norm (1 + w) + lm_head, fp32 | `colx.unembed.from_model`, fp32 |
| layers | 23 … 56 of 0-61 | 24 … 58 of 0-63 (same relative depths) |

Qwen3-4B (block F) uses the Qwen code paths with its own layers and lenses.
"""

from dataclasses import dataclass
from pathlib import Path

from colx import provenance, qwen
from colx.gemma import model as gemma
from colx.jlens.lens import LAYERS as QWEN_LAYERS
from colx.unembed import from_model


@dataclass(frozen=True)
class Backend:
    """What extraction and readout need to know about one model."""

    name: str
    layers: tuple[int, ...]
    lens_sha256: str
    family: str = ""

    @property
    def kind(self) -> str:
        """gemma or qwen: which loader, template and unembedding apply."""
        return self.family or self.name

    def load(self, model_dir: Path):
        """Tokenizer and model on the GPU."""
        if self.kind == "gemma":
            return gemma.load(model_dir)
        return qwen.load_tokenizer(str(model_dir)), qwen.load_model(str(model_dir))

    def render(self, tokenizer, system: str, user: str) -> str:
        """One call, rendered as it was sent for generation."""
        if self.kind == "gemma":
            return gemma.render(tokenizer, system, user)
        return qwen.render_chat(tokenizer, system, user)

    def render_user(self, tokenizer, user: str) -> str:
        """One user turn, no system prompt (the frozen judges)."""
        if self.kind == "gemma":
            messages = [{"role": "user", "content": user}]
            return tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        return qwen.render_chat(tokenizer, None, user)

    def blocks(self, model):
        """The decoder blocks (layer l = the output of block l)."""
        return gemma.decoder_layers(model) if self.kind == "gemma" else model.model.layers

    def unembed(self, model):
        """fp32 unembedding of residuals."""
        return gemma.Unembed(model) if self.kind == "gemma" else from_model(model)


# Qwen3-4B (block F): 36 layers; 10 layers over the same 38-92% band. Lens hashes: the
# Neuronpedia J-lens and J++ lens files (neuronpedia/jacobian-lens @ e166deb).
QWEN4B_LAYERS = (13, 15, 17, 19, 21, 24, 26, 28, 30, 32)
QWEN4B_LENSES = {
    "jlens": "9c94a43ac2db2debbab36acb74480f49a3ac411fb3d7fa8e5461377028e74606",
    "jpp": "893f7da243ab60d0628548a8c2b3afebaa45afdb1877d1c11521fde53209722d",
}

BACKENDS = {
    "gemma": Backend("gemma", gemma.LAYERS, gemma.LENS_SHA256),
    "qwen": Backend("qwen", QWEN_LAYERS, provenance.LENS_SHA256),
    "qwen4b": Backend("qwen4b", QWEN4B_LAYERS, QWEN4B_LENSES["jlens"], family="qwen"),
}
