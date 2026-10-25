"""Compute the exploratory pair scores and their tests; write `analysis/pair_scores.*`.

Instruments (plan follow-up A): judge agreement (one per run), and token overlap for the
words-relative and raw grids at P1 and P2. Tests: a, b, b_style, operating point and paired
by scenario (`suite.instrument_tests`), and pair found (`suite.pair_found`).
"""

import json
from pathlib import Path

import pandas as pd

from colx import provenance
from colx.joint.pairs import agreement_table, overlap_table
from colx.joint.suite import instrument_tests, pair_found
from colx.joint.write import LABELS
from colx.judge.inputs import ARMS as ROUND4_ARMS

TOKENS = {"rel": ROUND4_ARMS["rel"], "raw": "lens_tokens.parquet"}


def pair_instruments(out_dir: Path, round4_dir: Path) -> dict[str, pd.DataFrame]:
    """Run tables (run_id, run_score, pair, order) for each exploratory instrument."""
    scores = pd.read_parquet(out_dir / "scores.parquet")
    orders = {r: list(g["order"].iloc[0]) for r, g in scores.groupby("run_id")}
    tables = {"agreement": agreement_table(scores)}
    for rendering, path in TOKENS.items():
        tokens = pd.read_parquet(round4_dir / path)
        for position in ("P1", "P2"):
            tables[f"overlap_{rendering}_{position}"] = overlap_table(tokens, orders, position)
    return tables


def analyse_pairs(out_dir: Path, round4_dir: Path, n_boot: int, n_perm: int, log=print) -> list:
    """Test every instrument; save records and run tables; return the records."""
    runs = pd.read_parquet(round4_dir / "runs.parquet")
    agents = pd.read_parquet(round4_dir / "agents.parquet")
    labels = runs.rename(columns={"colluded": "run_colluded"})[LABELS]
    roles = agents.groupby("run_id").apply(lambda g: dict(zip(g.agent, g.role, strict=True)))
    coll = runs[runs["mode"] == "collusion"].set_index("run_id")["colluded"]
    records, frames = [], []
    for name, table in pair_instruments(out_dir, round4_dir).items():
        tagged = table.merge(labels, on="run_id")
        records += [{"instrument": name} | t for t in instrument_tests(tagged, n_boot, n_perm)]
        records += [{"instrument": name} | p for p in pair_found(table, roles, coll)]
        frames.append(tagged.assign(instrument=name))
        log(f"{name} done")
    folder = out_dir / "analysis"
    folder.mkdir(parents=True, exist_ok=True)
    meta = provenance.collect(
        "col lens-judge joint pair-scores", label="exploratory", n_boot=n_boot, n_perm=n_perm
    )
    (folder / "pair_scores.json").write_text(
        json.dumps(meta | {"tests": records}, indent=1, default=str)
    )
    out = pd.concat(frames, ignore_index=True)
    out["pair"] = out["pair"].map(lambda p: None if p is None else list(p))
    out.to_parquet(folder / "pair_scores.parquet", index=False)
    return records
