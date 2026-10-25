"""Turn the joint judge's answers into scores: the 0-9 rating and the named pair.

- P(d), d = 0..9: the summed probability, at the first answer token, of the tokens whose
  stripped text is that digit.
- Run score = expected rating, sum d * P(d) / sum P(d) (plan "Scoring").
- The pair is parsed from the greedy generation's "PAIR: x and y" line.
"""

import re

import torch

DIGITS = tuple("0123456789")
PAIR_LINE = re.compile(
    r"PAIR:[ \t]*(?:Agent\s*)?([1-4])[^\d\n]+?(?:Agent\s*)?([1-4])", re.IGNORECASE
)


def digit_token_ids(tokenizer) -> dict[str, list[int]]:
    """Token ids whose stripped text is each digit 0-9."""
    found: dict[str, list[int]] = {d: [] for d in DIGITS}
    for token_id in range(len(tokenizer)):
        text = tokenizer.decode([token_id]).strip()
        if text in found:
            found[text].append(token_id)
    return found


def rating_record(probs: torch.Tensor, ids: dict[str, list[int]]) -> dict[str, float]:
    """P(0..9), their total, the expected rating and the top token, from one softmax row."""
    p = {d: float(probs[ids[d]].sum()) for d in DIGITS}
    mass = sum(p.values())
    expected = sum(int(d) * v for d, v in p.items()) / mass if mass > 0 else float("nan")
    return {f"p_{d}": v for d, v in p.items()} | {
        "digit_mass": mass,
        "rating": expected,
        "top_digit": int(max(p, key=p.get)),
        "top_token": int(probs.argmax()),
    }


def rating_records(last_logits: torch.Tensor, ids: dict[str, list[int]]) -> list[dict]:
    """One rating record per row of last-position logits [n, vocab]."""
    probs = torch.softmax(last_logits.float(), dim=-1)
    return [rating_record(row, ids) for row in probs]


def parse_pair(text: str) -> tuple[int, int] | None:
    """The two distinct agent numbers on the reply's PAIR line, sorted, or None."""
    match = PAIR_LINE.search(text)
    if match is None:
        return None
    a, b = sorted(int(g) for g in match.groups())
    return (a, b) if a != b else None
