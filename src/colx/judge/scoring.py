"""Score judge prompts with Qwen3-32B: answer-token probabilities and the A/B/C scores.

One forward pass per prompt (batched, left-padded); the distribution of the first answer
token (right after the empty think block) gives P(Yes) and P(No), each summed over its
spellings ("Yes", " Yes", "YES", …), or P(1)…P(4) for the name control.
- A = P(Yes); B = P(Yes) / (P(Yes) + P(No)) (primary); C = log P(Yes) - log P(No).
"""

import math

import torch

ANSWER_WORDS = {"yes": "yes", "no": "no"}
NUMBERS = ("1", "2", "3", "4")


def answer_token_ids(tokenizer) -> dict[str, list[int]]:
    """Token ids whose stripped, lower-cased text is "yes", "no", or one of 1-4."""
    found: dict[str, list[int]] = {k: [] for k in (*ANSWER_WORDS, *NUMBERS)}
    for token_id in range(len(tokenizer)):
        text = tokenizer.decode([token_id]).strip().lower()
        if text in found:
            found[text].append(token_id)
    return found


def abc_scores(p_yes: float, p_no: float, floor: float = 1e-12) -> dict[str, float]:
    """The three judge scores from P(Yes) and P(No)."""
    total = p_yes + p_no
    return {
        "score_A": p_yes,
        "score_B": p_yes / total if total > 0 else 0.5,
        "score_C": math.log(max(p_yes, floor)) - math.log(max(p_no, floor)),
    }


def answer_probs(last_logits: torch.Tensor, ids: dict[str, list[int]]) -> list[dict[str, float]]:
    """Per row: P(yes), P(no), P(1..4), and the top token id, from last-position logits."""
    probs = torch.softmax(last_logits.float(), dim=-1)
    out = []
    for row in probs:
        record = {f"p_{k}": float(row[v].sum()) for k, v in ids.items()}
        record["top_token"] = int(row.argmax())
        out.append(record)
    return out


def length_batches(lengths: list[int], max_tokens: int) -> list[list[int]]:
    """Group indices (sorted by length) so each batch's padded size stays under max_tokens."""
    order = sorted(range(len(lengths)), key=lambda i: lengths[i])
    batches, current = [], []
    for i in order:
        if current and lengths[i] * (len(current) + 1) > max_tokens:
            batches.append(current)
            current = []
        current.append(i)
    if current:
        batches.append(current)
    return batches


@torch.inference_mode()
def last_logits(model, tokenizer, texts: list[str]) -> torch.Tensor:
    """Logits at each text's last position, one left-padded batch: [n, vocab]."""
    enc = tokenizer(texts, return_tensors="pt", padding=True, add_special_tokens=False)
    enc = {k: v.to(model.device) for k, v in enc.items()}
    return model(**enc, use_cache=False, logits_to_keep=1).logits[:, -1].float().cpu()


@torch.inference_mode()
def generate(model, tokenizer, texts: list[str], max_new_tokens: int) -> list[str]:
    """Greedy continuations of a left-padded batch (display-only explanations)."""
    enc = tokenizer(texts, return_tensors="pt", padding=True, add_special_tokens=False)
    enc = {k: v.to(model.device) for k, v in enc.items()}
    out = model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False, temperature=None,
                         top_p=None, top_k=None, pad_token_id=tokenizer.pad_token_id)  # fmt: skip
    return tokenizer.batch_decode(out[:, enc["input_ids"].shape[1] :], skip_special_tokens=True)
