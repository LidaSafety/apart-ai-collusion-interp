"""Assemble every judge prompt of the round-4 experiment into one table.

One row per prompt: which judge, rendering arm and position it belongs to, which agent it
is about, the prompt text, and the answer kind ("yesno", or "number" for the name control,
with the correct number). Judges (plan "Baselines and checks", amendment 1):

| judge | arms | positions | agents |
|---|---|---|---|
| lens | raw, rel | P1, P2 | all 400 |
| instruction_control | raw, rel | P1, P2 | 200 in collusion-mode runs |
| name_control | raw, rel | P1 | all 400 |
| judge_works, text, instruction_only, vote | - | - | all 400 |
"""

from pathlib import Path

import numpy as np
import pandas as pd

from colx.jlens.tokens import grids
from colx.judge import prompts
from colx.narcbench.runs import load_runs

ARMS = {"raw": "lens_grids.parquet", "rel": "filtered/lens_tokens_words_relative.parquet"}
NAME_SEED = 0


def load_grids(out_dir: Path) -> dict[str, pd.DataFrame]:
    """Rendered grids per arm, indexed by (run_id, agent_index, position)."""
    raw = pd.read_parquet(out_dir / ARMS["raw"])
    rel = grids(pd.read_parquet(out_dir / ARMS["rel"]))
    return {arm: g.set_index(["run_id", "agent_index", "position"])["grid"]
            for arm, g in (("raw", raw), ("rel", rel))}  # fmt: skip


def name_orders(agents: pd.DataFrame, seed: int = NAME_SEED) -> dict[str, list[str]]:
    """A fixed random order of each run's four names (seeded, runs in sorted order)."""
    rng = np.random.default_rng(seed)
    return {
        run_id: list(rng.permutation(group.sort_values("agent_index")["agent"].tolist()))
        for run_id, group in agents.groupby("run_id", sort=True)
    }


def _row(judge: str, agent: pd.Series, prompt: str, **extra) -> dict:
    """One prompt-table row."""
    base = {"judge": judge, "arm": "-", "position": "-", "run_id": agent["run_id"],
            "agent_index": int(agent["agent_index"]), "agent": agent["agent"],
            "kind": "yesno", "true_number": 0, "prompt": prompt}  # fmt: skip
    return base | extra


def lens_rows(agents: pd.DataFrame, briefs: pd.Series, grid: dict) -> list[dict]:
    """Lens judge, instruction control and name control prompts."""
    rows, orders = [], name_orders(agents)
    for _, a in agents.iterrows():
        brief = briefs[a["run_id"]]
        for arm, g in grid.items():
            for pos in ("P1", "P2"):
                tokens = g[(a["run_id"], a["agent_index"], pos)]
                where = {"arm": arm, "position": pos}
                rows.append(_row("lens", a, prompts.lens_prompt(brief, tokens, pos), **where))
                if a["mode"] == "collusion":
                    text = prompts.lens_prompt(brief, tokens, pos, prompts.INSTRUCTION_Q)
                    rows.append(_row("instruction_control", a, text, **where))
            names = orders[a["run_id"]]
            text = prompts.name_prompt(brief, g[(a["run_id"], a["agent_index"], "P1")], names)
            rows.append(_row("name_control", a, text, arm=arm, position="P1", kind="number",
                             true_number=names.index(a["agent"]) + 1))  # fmt: skip
    return rows


def text_rows(agents: pd.DataFrame, runs: pd.DataFrame, private: dict[str, str]) -> list[dict]:
    """Judge-works check and the text, instruction-only and vote baselines."""
    rows = []
    for _, a in agents.iterrows():
        run = runs.loc[a["run_id"]]
        brief, disc, name = run["brief"], run["discussion"], a["agent"]
        works = prompts.judge_works_prompt(brief, private[a["run_id"]], disc, name)
        rows += [
            _row("judge_works", a, works),
            _row("text", a, prompts.text_prompt(brief, disc, name)),
            _row("instruction_only", a, prompts.instruction_prompt(brief, a["system_prompt"])),
            _row("vote", a, prompts.vote_prompt(brief, a["vote_line"])),
        ]  # fmt: skip
    return rows


def build_prompts(out_dir: Path, core_dir: Path, run_ids: list[str] | None = None) -> pd.DataFrame:
    """The full prompt table (optionally only some runs, for the dry run)."""
    agents = pd.read_parquet(out_dir / "agents.parquet")
    runs = pd.read_parquet(out_dir / "runs.parquet").set_index("run_id")
    if run_ids is not None:
        agents = agents[agents["run_id"].isin(run_ids)]
    private = {r.run_id: "\n".join(r.private_messages) for r in load_runs(core_dir)}
    rows = lens_rows(agents, runs["brief"], load_grids(out_dir)) + text_rows(agents, runs, private)
    return pd.DataFrame(rows)
