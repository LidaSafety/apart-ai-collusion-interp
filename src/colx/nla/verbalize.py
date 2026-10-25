"""Describe activations with the NLA verbalizer (kitft's recipe, in plain transformers; GPU).

Recipe (`kitft/nla-inference`, `nla_meta.yaml`): the canonical prompt holds one marker
token (㈜, checked with its neighbours); its embedding row is replaced by the activation,
rescaled to the sidecar's L2 norm (60,000). Other rows are the model's own embeddings, which
already carry Gemma's x sqrt(d) scale. Greedy decoding; the description is the text inside
<explanation> tags. All prompts are the same length, so batches need no padding.
"""

import re
from pathlib import Path

import torch
import yaml
from transformers import AutoModelForCausalLM, AutoTokenizer

EXPLANATION = re.compile(r"<explanation>\s*(.*?)\s*(?:</explanation>|$)", re.DOTALL)


def explanation(text: str) -> str:
    """The text inside <explanation> tags (to the end if the tag is unclosed)."""
    match = EXPLANATION.search(text)
    return match.group(1).strip() if match else text.strip()


def rescale(v: torch.Tensor, norm: float) -> torch.Tensor:
    """Rescale rows to the given L2 norm (computed in fp32)."""
    v = v.float()
    return v / v.norm(dim=-1, keepdim=True).clamp_min(1e-12) * norm


class Verbalizer:
    """The NLA actor, its canonical prompt and the marker position."""

    def __init__(self, model_dir: Path) -> None:
        meta = yaml.safe_load((model_dir / "nla_meta.yaml").read_text())
        tok = meta["tokens"]
        self.norm = float(meta["extraction"]["injection_scale"])
        self.tokenizer = AutoTokenizer.from_pretrained(model_dir)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_dir, dtype=torch.bfloat16, device_map="cuda"
        ).eval()
        content = meta["prompt_templates"]["av"].format(injection_char=tok["injection_char"])
        ids = self.tokenizer.apply_chat_template(
            [{"role": "user", "content": content}], tokenize=True, add_generation_prompt=True
        )
        ids = list(ids["input_ids"] if isinstance(ids, dict) else ids)
        hits = [i for i, t in enumerate(ids) if t == tok["injection_token_id"]]
        assert len(hits) == 1, "marker must appear once in the canonical prompt"
        self.pos = hits[0]
        assert ids[self.pos - 1] == tok["injection_left_neighbor_id"]
        assert ids[self.pos + 1] == tok["injection_right_neighbor_id"]
        self.ids = torch.tensor([ids], device=self.model.device)

    @torch.inference_mode()
    def describe(self, vectors: torch.Tensor, max_new_tokens: int = 150) -> list[str]:
        """One description per activation row [n, d]."""
        base = self.model.get_input_embeddings()(self.ids)
        embeds = base.repeat(len(vectors), 1, 1)
        embeds[:, self.pos] = rescale(vectors.to(self.model.device), self.norm).to(embeds.dtype)
        mask = torch.ones(embeds.shape[:2], dtype=torch.long, device=embeds.device)
        out = self.model.generate(
            inputs_embeds=embeds,
            attention_mask=mask,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            temperature=None,
            top_p=None,
            top_k=None,
        )
        return [explanation(t) for t in self.tokenizer.batch_decode(out, skip_special_tokens=True)]
