"""Block F tests (exploratory): F1-F3 with each lens, and the paired J++ - J differences.

Each lens folder (`results/qwen4b-jlens`, `results/qwen4b-jpp`) holds the token tables of
the same Qwen3-4B activations (`results/qwen4b`: labels, calls, residuals).
- F1: the overlap detector at P1, collusion mode vs control (words-relative, raw);
- F2: the held-out instruction classifier at P1 (colluder vs honest, collusion-mode runs);
- F3: the held-out follow-through classifier at R3 T-start (colluders).
Differences: paired bootstrap over scenarios of the AUROC difference (`versus`), two-sided
read from its interval (the record keeps the one-sided lower bound and p).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from colx import provenance
from colx.analysis.suite import auroc_test
from colx.joint.pairs import overlap_table
from colx.joint.write import LABELS
from colx.turns import classify
from colx.turns.analyse import versus
from colx.turns.followup import lens_scores
from colx.turns.write import load_inputs


def f1_scores(tokens: pd.DataFrame, runs: pd.DataFrame, rendering: str) -> pd.DataFrame:
    """Overlap run scores at P1 with run labels (mode, scenario)."""
    orders = {r: sorted(g.agent.unique()) for r, g in tokens.groupby("run_id")}
    labels = runs.rename(columns={"colluded": "run_colluded"})[LABELS]
    return (
        overlap_table(tokens[tokens.rendering == rendering], orders, "P1")
        .merge(labels)
        .sort_values("run_id")
    )


def f2_scores(tokens: pd.DataFrame, agents: pd.DataFrame) -> tuple[np.ndarray, pd.DataFrame]:
    """Held-out P(colluder) at P1 for agents in collusion-mode runs (words-relative)."""
    keys = agents[agents["mode"] == "collusion"].sort_values(["run_id", "agent"], ignore_index=True)
    here = tokens[(tokens.rendering == "rel") & (tokens.position == "P1")]
    y = (keys.role == "colluder").to_numpy()
    folds = classify.scenario_folds(keys.scenario_id.to_numpy())
    return classify.heldout_scores(
        classify.presence_matrix(here, keys), y, folds, classify.lens_model
    ), keys


def lens_records(
    lens_dir: Path, base_dir: Path, core_dir: Path, n_boot: int, n_perm: int
) -> tuple[dict, dict]:
    """F1-F3 for one lens; also the raw scores, for the paired differences."""
    final = pd.read_parquet(lens_dir / "final_tokens.parquet")
    runs, agents = (
        pd.read_parquet(base_dir / "runs.parquet"),
        pd.read_parquet(base_dir / "agents.parquet"),
    )
    rec, raw = {}, {}
    for r in ("rel", "raw"):
        t = f1_scores(final, runs, r)
        y, scen = (t["mode"] == "collusion").to_numpy(), t.scenario_id.to_numpy()
        rec[f"f1_{r}"] = auroc_test(t.run_score, y, scen, scen, n_boot, n_perm)
        raw[f"f1_{r}"] = (t.run_score.to_numpy(), y, scen)
    s2, keys = f2_scores(final, agents)
    y2, sc2 = (keys.role == "colluder").to_numpy(), keys.scenario_id.to_numpy()
    rec["f2"] = auroc_test(s2, y2, sc2, np.zeros(len(y2), int), n_boot, n_perm)
    raw["f2"] = (s2, y2, sc2)
    turns, colluders, _, _, _ = load_inputs(lens_dir, base_dir, core_dir)
    s3, _, _ = lens_scores(turns, colluders, "rel")
    y3, sc3 = colluders.voted_target.to_numpy(bool), colluders.scenario_id.to_numpy()
    rec["f3"] = auroc_test(s3, y3, sc3, np.zeros(len(y3), int), n_boot, n_perm)
    raw["f3"] = (s3, y3, sc3)
    return rec, raw


def compare_lenses(
    base_dir: Path, core_dir: Path, lens_dirs: dict[str, Path], n_boot: int, n_perm: int
) -> dict:
    """Records per lens and J++ - J differences; save `lens_comparison.json` in base_dir."""
    recs, raws = {}, {}
    for name, d in lens_dirs.items():
        recs[name], raws[name] = lens_records(d, base_dir, core_dir, n_boot, n_perm)
    diffs = {
        k: versus(
            raws["jpp"][k][0], raws["jlens"][k][0], raws["jlens"][k][1], raws["jlens"][k][2], n_boot
        )
        for k in raws["jlens"]
    }
    out = {"lenses": recs, "jpp_minus_jlens": diffs}
    meta = provenance.collect(
        "col lens-judge lenscmp", label="exploratory", n_boot=n_boot, n_perm=n_perm
    )
    (base_dir / "lens_comparison.json").write_text(json.dumps(meta | out, indent=1, default=str))
    return out
