"""Data for the round-4 results app: read result files and shape them for charts.

The app never loads the model; everything here reads files written by `col lens-judge`.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from colx.jlens.tokens import grids

NAMES = {
    "lens": "Lens judge",
    "text": "Text baseline",
    "instruction_only": "Instruction only",
    "vote": "Vote baseline",
}
ARM_NAMES = {"raw": "raw", "rel": "words-relative", "-": ""}


def instrument_name(judge: str, arm: str, position: str) -> str:
    """Readable name, e.g. "Lens judge · words-relative · P2"."""
    parts = [NAMES.get(judge, judge), ARM_NAMES.get(arm, arm), "" if position == "-" else position]
    return " · ".join(p for p in parts if p)


def roc_points(scores: np.ndarray, labels: np.ndarray) -> pd.DataFrame:
    """ROC curve points (false-positive rate, true-positive rate), one per distinct threshold."""
    labels = np.asarray(labels, bool)
    thresholds = np.r_[np.inf, np.unique(scores)[::-1]]
    rows = [
        {"fpr": float((scores[~labels] >= t).mean()), "tpr": float((scores[labels] >= t).mean())}
        for t in thresholds
    ]
    return pd.DataFrame(rows)


def mistakes(runs: pd.DataFrame, k: int = 5) -> pd.DataFrame:
    """The k most confident false alarms and the k most confident misses (run level)."""
    false_alarms = runs[~runs.run_colluded].nlargest(k, "run_score").assign(kind="false alarm")
    misses = runs[runs.run_colluded].nsmallest(k, "run_score").assign(kind="miss")
    return pd.concat([false_alarms, misses], ignore_index=True)


def load_all(out_dir: Path) -> dict[str, pd.DataFrame | dict]:
    """Every file the app reads."""

    analysis = out_dir / "analysis"
    raw_grids = pd.read_parquet(out_dir / "lens_grids.parquet").assign(arm="raw")
    rel_grids = grids(
        pd.read_parquet(out_dir / "filtered" / "lens_tokens_words_relative.parquet")
    ).assign(arm="rel")
    return {
        "summary": json.loads((analysis / "summary.json").read_text()),
        "aurocs": json.loads((analysis / "aurocs.json").read_text()),
        "run_scores": pd.read_parquet(analysis / "run_scores.parquet"),
        "vote_share": pd.read_parquet(analysis / "vote_label_share.parquet"),
        "scores": pd.read_parquet(out_dir / "judge" / "scores.parquet"),
        "explanations": pd.read_parquet(out_dir / "judge" / "explanations.parquet"),
        "agents": pd.read_parquet(out_dir / "agents.parquet"),
        "runs": pd.read_parquet(out_dir / "runs.parquet"),
        "grids": pd.concat([raw_grids, rel_grids], ignore_index=True),
    }
