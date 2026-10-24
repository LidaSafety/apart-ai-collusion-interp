"""Run the joint judge: score every prompt, generate the pair and explanation (GPU).

Outputs under `results/joint-judge/` (or `judge-dryrun/` inside it):
- `pooled_tokens.parquet`, `prompts.parquet`: the inputs (see `inputs.py`);
- `scores.parquet`: per prompt, P(0..9), expected rating, top digit, the greedy reply and
  the pair parsed from it.
"""

import time
from pathlib import Path

import pandas as pd

from colx import provenance, qwen
from colx.joint.inputs import build_prompts
from colx.joint.scoring import digit_token_ids, parse_pair, rating_records
from colx.judge.run import DRY_RUNS, MAX_BATCH_TOKENS, explain_table, render_prompts
from colx.judge.scoring import last_logits, length_batches


def write_inputs(round4_dir: Path, folder: Path, run_ids: list[str] | None) -> pd.DataFrame:
    """Build and save the pooled tokens and the prompt table; return the prompt table."""
    folder.mkdir(parents=True, exist_ok=True)
    pooled, table = build_prompts(round4_dir, run_ids)
    meta = provenance.collect("col lens-judge joint", round4_dir=str(round4_dir))
    for name, frame in (("pooled_tokens", pooled), ("prompts", table)):
        frame.to_parquet(folder / f"{name}.parquet", index=False)
        provenance.write_meta(folder / f"{name}.parquet", meta)
    return table


def score_ratings(model, tokenizer, table: pd.DataFrame, log=print) -> pd.DataFrame:
    """Forward-pass every prompt; return one rating row per prompt (same order)."""
    texts, lengths = render_prompts(tokenizer, table)
    ids = digit_token_ids(tokenizer)
    records: list[dict | None] = [None] * len(texts)
    batches, start = length_batches(lengths, MAX_BATCH_TOKENS), time.time()
    for b, batch in enumerate(batches):
        logits = last_logits(model, tokenizer, [texts[i] for i in batch])
        for i, rec in zip(batch, rating_records(logits, ids), strict=True):
            records[i] = rec | {"n_tokens": lengths[i]}
        log(f"scored batch {b + 1}/{len(batches)} ({time.time() - start:.0f}s)")
    scores = pd.DataFrame(records)
    scores["top_token_text"] = [tokenizer.decode([t]) for t in scores["top_token"]]
    return scores


def format_check(scores: pd.DataFrame) -> dict[str, object]:
    """Dry-run checks only (no scores): a digit first, digit mass ≥ 0.5, a parseable pair."""
    return {
        "prompts": len(scores),
        "top token is a digit": int(scores["top_token_text"].str.strip().str.isdigit().sum()),
        "P(0..9) >= 0.5": int((scores["digit_mass"] >= 0.5).sum()),
        "min P(0..9)": round(float(scores["digit_mass"].min()), 3),
        "PAIR line parsed": int(scores["pair"].notna().sum()),
    }


def run_joint(model_path: str, round4_dir: Path, out_dir: Path, dry_run: bool, log=print) -> dict:
    """Build prompts, score them, generate replies, parse pairs, save with provenance."""
    folder = (out_dir / "judge-dryrun") if dry_run else out_dir
    table = write_inputs(round4_dir, folder, DRY_RUNS if dry_run else None)
    log(f"{len(table)} prompts")
    tokenizer, model = qwen.load_tokenizer(model_path), qwen.load_model(model_path)
    tokenizer.padding_side = "left"
    meta = provenance.collect("col lens-judge joint judge", dry_run=dry_run, model_path=model_path)
    scores = score_ratings(model, tokenizer, table, log)
    replies = explain_table(
        model, tokenizer, table, folder / "replies.partial.parquet", log, judges=("joint",)
    )
    pairs = [parse_pair(text) for text in replies["explanation"]]
    out = pd.concat([table.drop(columns=["prompt"]), scores], axis=1).assign(
        reply=replies["explanation"].to_numpy(), pair=[list(p) if p else None for p in pairs]
    )
    out.to_parquet(folder / "scores.parquet", index=False)
    provenance.write_meta(folder / "scores.parquet", meta)
    return format_check(out)
