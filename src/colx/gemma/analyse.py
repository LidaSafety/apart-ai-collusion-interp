"""The Gemma plan's tests (docs/plans/gemma.md, "Tests") and its primary family.

- Tests 1-2: the no-LLM token-overlap score at P1 (words-relative, raw), collusion-mode vs
  control runs: AUROC, scenario bootstrap, shuffle within scenario.
- Test 3: the R3 T-start follow-through classifier, from `col lens-judge turns analyse`.
- Test 4: lens minus the frozen text judge at R3 T-start, from `col lens-judge turns follow-up`.
- Secondary: overlap tests a and b (and the rest of `instrument_tests`), and the held-out
  instruction classifier at P1 (colluders vs honest agents in collusion-mode runs).
Primary family: tests 1-4, Holm, one-sided alpha 0.05.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from colx import provenance
from colx.analysis.stats import holm
from colx.analysis.suite import auroc_test
from colx.joint.pairs import overlap_table
from colx.joint.suite import instrument_tests
from colx.joint.write import LABELS
from colx.turns import classify


def overlap_tests(tokens: pd.DataFrame, runs: pd.DataFrame, n_boot: int, n_perm: int) -> list:
    """Tests 1-2 and the overlap secondaries, for each rendering at P1."""
    labels = runs.rename(columns={"colluded": "run_colluded"})[LABELS]
    orders = {r: sorted(g.agent.unique()) for r, g in tokens.groupby("run_id")}
    out = []
    for rendering in ("rel", "raw"):
        table = overlap_table(tokens[tokens.rendering == rendering], orders, "P1").merge(labels)
        mode = (table["mode"] == "collusion").to_numpy()
        scen = table.scenario_id.to_numpy()
        tag = {"instrument": f"overlap_{rendering}_P1"}
        out.append(
            tag
            | {"test": "mode_vs_control"}
            | auroc_test(table.run_score, mode, scen, scen, n_boot, n_perm)
        )
        out += [tag | t for t in instrument_tests(table, n_boot, n_perm)]
    return out


def instruction_classifier(
    tokens: pd.DataFrame, agents: pd.DataFrame, n_boot: int, n_perm: int
) -> dict:
    """Held-out (by scenario) classifier at P1: colluder vs honest, collusion-mode runs."""
    keys = agents[agents["mode"] == "collusion"].sort_values(["run_id", "agent"], ignore_index=True)
    here = tokens[(tokens.rendering == "rel") & (tokens.position == "P1")]
    x = classify.presence_matrix(here, keys)
    y = (keys.role == "colluder").to_numpy()
    folds = classify.scenario_folds(keys.scenario_id.to_numpy())
    s = classify.heldout_scores(x, y, folds, classify.lens_model)
    scen = keys.scenario_id.to_numpy()
    return {
        "instrument": "instruction_classifier_rel_P1",
        "test": "colluder_vs_honest",
    } | auroc_test(s, y, scen, np.zeros(len(y), int), n_boot, n_perm)


def primary(overlap: list, out_dir: Path) -> list[dict]:
    """Tests 1-4 and their Holm verdicts."""
    turns = json.loads((out_dir / "analysis" / "tests.json").read_text())["tests"]
    follow = json.loads((out_dir / "analysis" / "follow_up.json").read_text())["tests"]
    pick = lambda rows, **k: next(r for r in rows if all(r.get(a) == b for a, b in k.items()))  # noqa: E731
    rows = {
        "1_overlap_rel_mode": pick(overlap, instrument="overlap_rel_P1", test="mode_vs_control"),
        "2_overlap_raw_mode": pick(overlap, instrument="overlap_raw_P1", test="mode_vs_control"),
        "3_r3_classifier": pick(
            turns, instrument="lens_rel", test="follow_through", round=3, position="T-start"
        ),
        "4_lens_minus_text": pick(follow, instrument="lens_rel", test="minus_text_judge"),
    }
    rejected = holm({k: r["p"] for k, r in rows.items()})
    return [
        {
            "name": k,
            "estimate": r.get("auroc", r.get("diff")),
            "ci_low": r.get("ci_low"),
            "ci_high": r.get("ci_high"),
            "lower_95": r.get("lower_95"),
            "p": r["p"],
            "holm_rejected": rejected[k],
        }
        for k, r in rows.items()
    ]


def analyse(out_dir: Path, n_boot: int, n_perm: int) -> list[dict]:
    """Run the Gemma-specific tests, combine the primary family, save; return the family."""
    tokens = pd.read_parquet(out_dir / "final_tokens.parquet")
    runs, agents = (
        pd.read_parquet(out_dir / "runs.parquet"),
        pd.read_parquet(out_dir / "agents.parquet"),
    )
    overlap = overlap_tests(tokens, runs, n_boot, n_perm)
    records = [*overlap, instruction_classifier(tokens, agents, n_boot, n_perm)]
    family = primary(overlap, out_dir)
    meta = provenance.collect("col lens-judge gemma analyse", n_boot=n_boot, n_perm=n_perm)
    (out_dir / "analysis" / "gemma_tests.json").write_text(
        json.dumps(meta | {"tests": records}, indent=1, default=str)
    )
    (out_dir / "analysis" / "gemma_summary.json").write_text(
        json.dumps(meta | {"primary": family}, indent=1, default=str)
    )
    return family
