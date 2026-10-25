"""ROC curves on NARCBench-Stego for the report's audit appendix (fig_stego_roc).

Per stego set, collusion vs control tables: the prompted Gemma monitor (expected 0-9
rating) as a curve, and NARCBench's built-in pit boss, which outputs only a yes/no flag, as
a single point. The overlap monitor's stego results stay in the text (report Appendix G):
its raw score separates the tables by finding the honest pair, which a curve would hide.
Shoes excluded by the stego plan's amendment 1 are left out, as in the primary analysis.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import roc_auc_score, roc_curve

from colx.overlap.figures import BLUE, FULL, _clean, _save, _title

# (results folder, transcript folder under /workspace/lens-judge/<set>/transcripts, panel title)
SETS = (
    ("stego-v1", "stego", "v1: count history leaked"),
    ("stego-v2", "stego-v2", "v2: leaks fixed"),
    ("stego-v2rep", "stego-v2rep", "v2 replication, new shoes"),
)
SERIES = (("rating", "Off-the-shelf Gemma, prompted to look for coded talk", BLUE),)


def shoe(run_id: str) -> str:
    """The shoe of a stego run id, e.g. 'bj__shoe08__collusion' -> 'shoe08'."""
    return run_id.split("__")[1]


def pit_boss_point(flags: pd.DataFrame) -> tuple[float, float]:
    """(false-positive rate, true-positive rate) of a yes/no flag over collusion and controls."""
    coll, ctrl = flags[flags["mode"] == "collusion"], flags[flags["mode"] == "control"]
    return float(ctrl.flagged.mean()), float(coll.flagged.mean())


def table_scores(results: Path, excluded: set[str]) -> pd.DataFrame:
    """Per table: mode and the prompted monitor's rating."""
    scores = pd.read_parquet(results / "monitor.parquet")[["run_id", "mode", "rating"]]
    return scores[~scores.run_id.map(shoe).isin(excluded)].reset_index(drop=True)


def pit_boss_flags(transcripts: Path, excluded: set[str]) -> pd.DataFrame:
    """The built-in pit boss's flag for every table, from NARCBench's own results files."""
    rows = []
    for f in sorted(transcripts.glob("*/results.json")):
        d = json.loads(f.read_text())
        rows.append({"run_id": f.parent.name, "mode": d["mode"], "flagged": bool(d["flagged"])})
    flags = pd.DataFrame(rows)
    return flags[~flags.run_id.map(shoe).isin(excluded)].reset_index(drop=True)


def _panel(ax, scores: pd.DataFrame, flags: pd.DataFrame, title: str, letter: str) -> None:
    """One set's ROC curves with their AUROCs, the chance line and the pit boss point."""
    y = (scores["mode"] == "collusion").astype(int)
    for k, (col, name, colour) in enumerate(SERIES):
        fpr, tpr, _ = roc_curve(y, scores[col])
        auc = roc_auc_score(y, scores[col])
        ax.plot(fpr, tpr, color=colour, lw=1.6, label=name)
        ax.text(0.97, 0.05 + 0.1 * k, f"AUROC {auc:.2f}", color=colour, ha="right",
                fontsize=7.5, transform=ax.transAxes)  # fmt: skip
    fp, tp = pit_boss_point(flags)
    label = "NARCBench pit boss (yes/no flag: one point)"
    ax.plot([fp], [tp], "o", ms=7, mfc="white", mec="black", mew=1.4, clip_on=False, label=label)
    ax.plot([0, 1], [0, 1], color="#555", ls=(0, (3, 3)), lw=0.7)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.set_aspect("equal")
    ax.set_xlabel("False-positive rate")
    _title(ax, letter, title)
    _clean(ax)


def stego_roc_figure(out: Path, results: Path = Path("results"),
                     transcripts: Path = Path("/workspace/lens-judge")) -> None:  # fmt: skip
    """Three panels, one per stego set (fig_stego_roc)."""
    fig, axes = plt.subplots(1, 3, figsize=(FULL, 3.0))
    for ax, (folder, sub, title), letter in zip(axes, SETS, "abc", strict=True):
        tests = json.loads((results / folder / "analysis" / "stego_tests.json").read_text())
        excluded = set(tests["tests"]["excluded_shoes"])
        scores = table_scores(results / folder, excluded)
        flags = pit_boss_flags(transcripts / folder / "transcripts" / sub, excluded)
        _panel(ax, scores, flags, title, letter)
    axes[0].set_ylabel("True-positive rate")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.tight_layout(w_pad=1.5, rect=(0, 0.1, 1, 1))
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, fontsize=7.5)
    _save(fig, out, "fig_stego_roc")
