"""Block D tests (exploratory): does the private-channel turn predict follow-through?

Among the 100 Core colluders (73 voted the target): a held-out (by scenario) lens
classifier at P-start and P-end, words-relative and raw, as for the discussion turns
(`colx.turns.analyse.classifier_tests`), against the style baseline; and, when present,
against a frozen Qwen judge reading the same private messages (`private_judge.parquet`).
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from colx import provenance
from colx.analysis.suite import auroc_test
from colx.turns import classify
from colx.turns.analyse import classifier_tests
from colx.turns.write import load_inputs


def analyse(
    out_dir: Path, round4_dir: Path, core_dir: Path, n_boot: int, n_perm: int
) -> list[dict]:
    """All D tests; save `analysis/private_tests.json`."""
    _, colluders, _, _, _ = load_inputs(Path("results/discussion-turns"), round4_dir, core_dir)
    tokens = pd.read_parquet(out_dir / "private_tokens.parquet")
    y = colluders.voted_target.to_numpy(bool)
    folds = classify.scenario_folds(colluders.scenario_id.to_numpy())
    style = classify.heldout_scores(
        colluders[["style", "style_group"]], y, folds, classify.style_model
    )
    baselines = {"style": style}
    judge_path = out_dir / "private_judge.parquet"
    records = []
    if judge_path.exists():
        judge = colluders.merge(pd.read_parquet(judge_path), on=["run_id", "agent"], how="left")[
            "score"
        ].to_numpy()
        baselines["text_judge"] = judge
        records.append(
            {"instrument": "text_judge"}
            | auroc_test(judge, y, colluders.scenario_id, np.zeros(len(y), int), n_boot, n_perm)
        )
    for position in ("P-start", "P-end"):
        for rendering in ("rel", "raw"):
            here = tokens[(tokens.position == position) & (tokens.rendering == rendering)]
            s = classify.heldout_scores(
                classify.presence_matrix(here, colluders), y, folds, classify.lens_model
            )
            records += [
                {"instrument": f"lens_{rendering}", "position": position} | t
                for t in classifier_tests(colluders, s, baselines, n_boot, n_perm)
            ]
    meta = provenance.collect(
        "col lens-judge private analyse", label="exploratory", n_boot=n_boot, n_perm=n_perm
    )
    (out_dir / "analysis").mkdir(parents=True, exist_ok=True)
    (out_dir / "analysis" / "private_tests.json").write_text(
        json.dumps(meta | {"tests": records}, indent=1, default=str)
    )
    return records
