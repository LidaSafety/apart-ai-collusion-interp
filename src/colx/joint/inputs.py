"""Assemble the joint judge's prompt table: one row per run and instrument.

Instruments (plan amendment 1): lens_rel, lens_raw, lens_pooled and both at P1 and P2,
plus discussion, so 900 prompts for 100 runs. The grids are round 4's, unchanged
(`lens_grids.parquet` and the words-relative table); the pooled lists come from
`pooled.py`. Each run's agents appear in one fixed random order (round 4's `name_orders`,
seed 0), stored with the row so the named pair can be checked later.
"""

from pathlib import Path

import pandas as pd

from colx.jlens.pooled import pooled_table
from colx.joint.prompts import RENDERING, joint_prompt
from colx.judge.inputs import ARMS as ROUND4_ARMS
from colx.judge.inputs import load_grids, name_orders

INSTRUMENTS = (
    *((arm, pos) for arm in ("lens_rel", "lens_raw", "lens_pooled") for pos in ("P1", "P2")),
    ("discussion", "-"),
    ("both", "P1"),
    ("both", "P2"),
)


def run_rows(run: pd.Series, names: list[str], lens: pd.Series) -> list[dict]:
    """The prompt rows of one run; `lens` is indexed by (rendering, agent name, position)."""
    rows = []
    for arm, position in INSTRUMENTS:
        shown = None
        if arm != "discussion":
            shown = [lens[(RENDERING[arm], name, position)] for name in names]
        text = joint_prompt(arm, run["brief"], names, run["discussion"], shown, position)
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


def lens_texts(round4_dir: Path, agents: pd.DataFrame, pooled: pd.DataFrame) -> pd.Series:
    """Every agent's lens text, indexed by (rendering, run_id, agent name, position)."""
    names = agents.set_index(["run_id", "agent_index"])["agent"]
    parts = []
    for rendering, grid in load_grids(round4_dir).items():
        keys = [(rendering, r, names[(r, i)], p) for r, i, p in grid.index]
        parts.append(pd.Series(grid.to_numpy(), index=pd.MultiIndex.from_tuples(keys)))
    keys = [("pooled", *k) for k in zip(pooled.run_id, pooled.agent, pooled.position, strict=True)]
    parts.append(pd.Series(pooled["pooled"].to_numpy(), index=pd.MultiIndex.from_tuples(keys)))
    return pd.concat(parts)


def build_prompts(
    round4_dir: Path, run_ids: list[str] | None = None
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The pooled-token table and the prompt table (optionally only some runs)."""
    agents = pd.read_parquet(round4_dir / "agents.parquet")
    runs = pd.read_parquet(round4_dir / "runs.parquet")
    pooled = pooled_table(pd.read_parquet(round4_dir / ROUND4_ARMS["rel"]))
    lens = lens_texts(round4_dir, agents, pooled)
    if run_ids is not None:
        agents, runs = agents[agents.run_id.isin(run_ids)], runs[runs.run_id.isin(run_ids)]
        pooled = pooled[pooled.run_id.isin(run_ids)]
    orders = name_orders(agents)
    rows = [
        row
        for _, run in runs.sort_values("run_id").iterrows()
        for row in run_rows(run, orders[run["run_id"]], lens.xs(run["run_id"], level=1))
    ]
    return pooled, pd.DataFrame(rows)
