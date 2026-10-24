"""Run the discussion-turn tests and write `results/discussion-turns/analysis/`."""

import json
from pathlib import Path

import pandas as pd

from colx import provenance
from colx.turns.analyse import all_tests


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
