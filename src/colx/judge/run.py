"""Run the judges: score every prompt, generate explanations, write the results (GPU).

Outputs under `results/round4-judge/judge/` (or `judge-dryrun/`):
- `prompts.parquet`: the prompt table (see `inputs.py`);
- `scores.parquet`: per prompt, P(Yes), P(No), P(1..4), A/B/C scores, the top answer token;
- `explanations.parquet`: greedy 2-3 sentence answers for the lens judge and text baseline.
"""

import time
from pathlib import Path

import pandas as pd

from colx import provenance, qwen
from colx.judge.inputs import build_prompts
from colx.judge.scoring import (
    abc_scores,
    answer_probs,
    answer_token_ids,
    generate,
    last_logits,
    length_batches,
)

MAX_BATCH_TOKENS = 24_000
GEN_BATCH = 16
GEN_TOKENS = 120
EXPLAIN = ("lens", "text")
DRY_RUNS = ["deception__audit_01__collusion", "deception__audit_01__control"]


def _render(tokenizer, table: pd.DataFrame) -> tuple[list[str], list[int]]:
    """Chat-rendered prompts (one user turn, thinking off) and their token lengths."""
    texts = [qwen.render_chat(tokenizer, None, p) for p in table["prompt"]]
    lengths = [len(ids) for ids in tokenizer(texts, add_special_tokens=False)["input_ids"]]
    return texts, lengths


def score_table(model, tokenizer, table: pd.DataFrame, log=print) -> pd.DataFrame:
    """Forward-pass every prompt; return one score row per prompt (same order)."""
    texts, lengths = _render(tokenizer, table)
    ids = answer_token_ids(tokenizer)
    records: list[dict | None] = [None] * len(texts)
    batches, start = length_batches(lengths, MAX_BATCH_TOKENS), time.time()
    for b, batch in enumerate(batches):
        for i, rec in zip(
            batch,
            answer_probs(last_logits(model, tokenizer, [texts[i] for i in batch]), ids),
            strict=True,
        ):
            records[i] = rec | abc_scores(rec["p_yes"], rec["p_no"]) | {"n_tokens": lengths[i]}
        if b % 20 == 0 or b == len(batches) - 1:
            log(f"scored batch {b + 1}/{len(batches)} ({time.time() - start:.0f}s)")
    scores = pd.DataFrame(records)
    scores["top_token_text"] = [tokenizer.decode([t]) for t in scores["top_token"]]
    return pd.concat([table.drop(columns=["prompt"]).reset_index(drop=True), scores], axis=1)


def explain_table(model, tokenizer, table: pd.DataFrame, log=print) -> pd.DataFrame:
    """Greedy explanations for the lens judge and the text baseline."""
    sub = table[table["judge"].isin(EXPLAIN)].reset_index(drop=True)
    texts, lengths = _render(tokenizer, sub)
    order = sorted(range(len(texts)), key=lambda i: lengths[i])
    answers: list[str] = [""] * len(texts)
    start = time.time()
    for k in range(0, len(order), GEN_BATCH):
        chunk = order[k : k + GEN_BATCH]
        for i, text in zip(
            chunk, generate(model, tokenizer, [texts[i] for i in chunk], GEN_TOKENS), strict=True
        ):
            answers[i] = text.strip()
        if (k // GEN_BATCH) % 10 == 0:
            log(f"explained {k + len(chunk)}/{len(order)} ({time.time() - start:.0f}s)")
    return sub.drop(columns=["prompt"]).assign(explanation=answers)


def format_check(scores: pd.DataFrame) -> dict[str, object]:
    """Dry-run checks only (no scores): answers start with an answer token, mass ≥ 0.5."""
    yesno = scores[scores["kind"] == "yesno"]
    number = scores[scores["kind"] == "number"]
    mass = yesno["p_yes"] + yesno["p_no"]
    top_yesno = yesno["top_token_text"].str.strip().str.lower().isin(["yes", "no"])
    num_mass = number[[f"p_{n}" for n in "1234"]].sum(axis=1)
    return {
        "yes/no prompts": len(yesno),
        "top token is Yes/No": int(top_yesno.sum()),
        "P(Yes)+P(No) >= 0.5": int((mass >= 0.5).sum()),
        "min P(Yes)+P(No)": round(float(mass.min()), 3),
        "number prompts": len(number),
        "top token is 1-4": int(number["top_token_text"].str.strip().isin(list("1234")).sum()),
        "min P(1..4)": round(float(num_mass.min()), 3) if len(number) else None,
    }  # fmt: skip


def run_judges(model_path: str, out_dir: Path, core_dir: Path, dry_run: bool, log=print) -> dict:
    """Build prompts, score them, explain (full run only), save with provenance."""
    folder = out_dir / ("judge-dryrun" if dry_run else "judge")
    folder.mkdir(parents=True, exist_ok=True)
    table = build_prompts(out_dir, core_dir, DRY_RUNS if dry_run else None)
    table.to_parquet(folder / "prompts.parquet", index=False)
    log(f"{len(table)} prompts")
    tokenizer, model = qwen.load_tokenizer(model_path), qwen.load_model(model_path)
    tokenizer.padding_side = "left"
    scores = score_table(model, tokenizer, table, log)
    meta = provenance.collect("col lens-judge judge", dry_run=dry_run, model_path=model_path)
    scores.to_parquet(folder / "scores.parquet", index=False)
    provenance.write_meta(folder / "scores.parquet", meta)
    checks = format_check(scores)
    if not dry_run:
        explained = explain_table(model, tokenizer, table, log)
        explained.to_parquet(folder / "explanations.parquet", index=False)
        provenance.write_meta(folder / "explanations.parquet", meta)
    return checks
