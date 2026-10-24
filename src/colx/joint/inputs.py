"""Assemble the joint judge's prompt table: one row per run and instrument.

Instruments: (lens, P1), (lens, P2), (discussion, -), (both, P1), (both, P2), so 500
prompts for 100 runs. Each run's agents appear in one fixed random order (round 4's
`name_orders`, seed 0), stored with the row so the named pair can be checked later.
"""

from pathlib import Path

import pandas as pd

from colx.jlens.pooled import pooled_table
from colx.joint.prompts import joint_prompt
from colx.judge.inputs import ARMS as ROUND4_ARMS
from colx.judge.inputs import name_orders

INSTRUMENTS = (("lens", "P1"), ("lens", "P2"), ("discussion", "-"), ("both", "P1"), ("both", "P2"))


def run_rows(run: pd.Series, names: list[str], pooled: pd.Series) -> list[dict]:
    """The 5 prompt rows of one run; `pooled` is indexed by (agent name, position)."""
    rows = []
    for arm, position in INSTRUMENTS:
        tokens = None if arm == "discussion" else [pooled[(n, position)] for n in names]
        text = joint_prompt(arm, run["brief"], names, run["discussion"], tokens, position)
        rows.append(
            {
                "judge": "joint",
                "arm": arm,
                "position": position,
                "run_id": run["run_id"],
                "order": names,
                "prompt": text,
            }
        )
    return rows


def build_prompts(
    round4_dir: Path, run_ids: list[str] | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The pooled-token table and the prompt table (optionally only some runs)."""
    agents = pd.read_parquet(round4_dir / "agents.parquet")
    runs = pd.read_parquet(round4_dir / "runs.parquet")
    pooled = pooled_table(pd.read_parquet(round4_dir / ROUND4_ARMS["rel"]))
    if run_ids is not None:
        agents, runs = agents[agents.run_id.isin(run_ids)], runs[runs.run_id.isin(run_ids)]
        pooled = pooled[pooled.run_id.isin(run_ids)]
    orders = name_orders(agents)
    by_run = pooled.set_index(["run_id", "agent", "position"])["pooled"]
    rows = [
        row
        for _, run in runs.sort_values("run_id").iterrows()
        for row in run_rows(run, orders[run["run_id"]], by_run.loc[run["run_id"]])
    ]
    return pooled, pd.DataFrame(rows)
