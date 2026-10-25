"""Run the discussion-turn tests and write `results/discussion-turns/analysis/`."""

import json
from pathlib import Path

import pandas as pd

from colx import provenance
from colx.turns.analyse import all_tests
from colx.turns.followup import compare, lens_scores, top_features


def load_inputs(out_dir: Path, round4_dir: Path, core_dir: Path):
    """Token table, the 100 colluders with labels, run labels, agents, public messages."""
    tokens = pd.read_parquet(out_dir / "turns_tokens.parquet")
    agents = pd.read_parquet(round4_dir / "agents.parquet")
    runs = pd.read_parquet(round4_dir / "runs.parquet")
    colluders = (
        agents[agents.role == "colluder"]
        .merge(runs[["run_id", "style_group"]], on="run_id")
        .sort_values(["run_id", "agent"], ignore_index=True)
    )
    messages = {
        r: json.loads((core_dir / r / "results.json").read_text())["public_messages"]
        for r in runs.run_id
    }
    return tokens, colluders, runs, agents, messages


def analyse(
    out_dir: Path, round4_dir: Path, core_dir: Path, n_boot: int, n_perm: int, log=print
) -> list[dict]:
    """Run all tests; save `tests.json` and `summary.json`; return the primary family."""
    records, family = all_tests(*load_inputs(out_dir, round4_dir, core_dir), n_boot, n_perm, log)
    folder = out_dir / "analysis"
    folder.mkdir(parents=True, exist_ok=True)
    meta = provenance.collect("col lens-judge turns analyse", n_boot=n_boot, n_perm=n_perm)
    (folder / "tests.json").write_text(json.dumps(meta | {"tests": records}, indent=1, default=str))
    summary = meta | {"label": "planned (docs/plans/discussion-turns.md)", "primary": family}
    (folder / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    return family


def follow_up(out_dir: Path, round4_dir: Path, core_dir: Path, n_boot: int, n_perm: int):
    """Follow-up B: compare with the text judge, list features; save both; return them."""
    tokens, colluders, _, _, _ = load_inputs(out_dir, round4_dir, core_dir)
    judged = pd.read_parquet(out_dir / "text_judge.parquet")
    text = colluders.merge(judged, on=["run_id", "agent"], how="left", validate="one_to_one")[
        "score"
    ]
    lens, features = {}, []
    for rendering in ("rel", "raw"):
        lens[rendering], x, here = lens_scores(tokens, colluders, rendering)
        features.append(top_features(x, here, colluders).assign(rendering=rendering))
    records = compare(text.to_numpy(), lens, colluders, n_boot, n_perm)
    folder = out_dir / "analysis"
    meta = provenance.collect("col lens-judge turns follow-up", n_boot=n_boot, n_perm=n_perm)
    (folder / "follow_up.json").write_text(
        json.dumps(meta | {"tests": records}, indent=1, default=str)
    )
    table = pd.concat(features, ignore_index=True)
    table.to_csv(folder / "r3_features.csv", index=False)
    return records, table
