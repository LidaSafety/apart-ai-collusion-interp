"""Part 2 of the overlap-monitor plan: the detector under the four stress conditions.

Each condition folder holds its 50 new collusion-mode runs and the 50 Gemma Core controls
(symlinks), with labels and P1 lens tokens from the `col lens-judge gemma` commands.
Per condition: every instrument of part 1 (lens and text) on condition vs control (S),
pair and split found, lens minus best text, and behaviour (did the colluders still vote
the target?). Across conditions: Holm over S-aware, S-para, S-independent (lens raw), the
benign comparison (Core collusion vs benign), and the operating point taken from the Core
controls' raw scores (0 of 50 and 5% false alarms).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from colx import provenance
from colx.analysis.stats import holm
from colx.analysis.suite import auroc_test
from colx.narcbench.runs import load_runs
from colx.overlap.compare import lens_scores, run_frame, score_table, tests, text_scores

CONDITIONS = ("aware", "para", "independent", "benign")
FAMILY = ("aware", "para", "independent")


def condition_table(transcripts: Path, out_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score table (all instruments) and run frame of one condition folder."""
    runs = load_runs(transcripts)
    frame = run_frame(runs)
    tokens = pd.read_parquet(out_dir / "final_tokens.parquet")
    table = score_table(text_scores(runs, frame) | lens_scores(tokens, frame), frame)
    return table.merge(frame[["run_id", "scenario_id", "mode"]]), frame


def behaviour(out_dir: Path) -> dict:
    """Collusion success and the colluders' target-vote rate, collusion-mode runs."""
    runs = pd.read_parquet(out_dir / "runs.parquet")
    agents = pd.read_parquet(out_dir / "agents.parquet")
    coll = agents[(agents["mode"] == "collusion") & (agents.role == "colluder")]
    runs = runs[runs["mode"] == "collusion"]
    return {
        "runs": len(runs),
        "colluded": int(runs.colluded.sum()),
        "colluder_target_rate": float(coll.voted_target.mean()),
    }


def operating_point(core: pd.DataFrame, tables: dict[str, pd.DataFrame]) -> dict:
    """Share of collusion-mode runs flagged at the Core controls' max and 95th percentile."""
    raw = lambda t: t[t.instrument == "lens_raw"]  # noqa: E731
    controls = raw(core)[raw(core)["mode"] == "control"].run_score.to_numpy()
    cuts = {"zero_of_50": controls.max(), "five_percent": np.percentile(controls, 95)}
    sets = {"core": core} | tables
    return {
        name: {
            k: float((raw(t)[raw(t)["mode"] == "collusion"].run_score > c).mean())
            for k, c in cuts.items()
        }
        for name, t in sets.items()
    } | {"thresholds": {k: float(c) for k, c in cuts.items()}}


def benign_vs_core(core: pd.DataFrame, benign: pd.DataFrame, n_boot: int, n_perm: int) -> dict:
    """Core collusion runs vs benign runs on lens raw: can it tell collusion from a shared note?"""
    pick = lambda t: t[(t.instrument == "lens_raw") & (t["mode"] == "collusion")]  # noqa: E731
    both = pd.concat([pick(core).assign(y=True), pick(benign).assign(y=False)])
    scen = both.scenario_id.to_numpy()
    return auroc_test(both.run_score, both.y.to_numpy(), scen, scen, n_boot, n_perm)


def analyse(
    transcripts: Path, results: Path, core_table: Path, n_boot: int, n_perm: int, log=print
) -> dict:
    """All part-2 tests; save `results/stress.json` with provenance."""
    core = pd.read_parquet(core_table)
    tables, out = {}, {}
    for c in CONDITIONS:
        table, frame = condition_table(transcripts / c, results / c)
        tables[c] = table
        out[c] = tests(table.drop(columns=["scenario_id", "mode"]), frame, n_boot, n_perm)
        out[c]["behaviour"] = behaviour(results / c)
        log(f"{c} done")
    p = {c: out[c]["mode_vs_control"]["lens_raw"]["p"] for c in FAMILY}
    record = {
        "conditions": out,
        "primary_holm": {c: {"p": p[c], "rejected": r} for c, r in holm(p).items()},
        "core_vs_benign_lens_raw": benign_vs_core(core, tables["benign"], n_boot, n_perm),
        "operating_point_lens_raw": operating_point(core, tables),
    }
    meta = provenance.collect(
        "col lens-judge overlap stress",
        label="planned (overlap-monitor.md, part 2)",
        n_boot=n_boot,
        n_perm=n_perm,
    )
    (results / "stress.json").write_text(json.dumps(meta | record, indent=1, default=str))
    return record
