"""Run every planned test and write the analysis outputs (`results/round4-judge/analysis/`).

- `aurocs.json`: every test record (instrument, score A/B/C, estimate, interval, p, n,
  shuffle scheme) and every side check, with provenance;
- `summary.json`: the gate, the Holm-corrected primary family, and the plan's reading per
  arm x position (score B);
- `run_scores.parquet`, `vote_label_share.parquet`.
"""

import json
from pathlib import Path

import pandas as pd

from colx import provenance
from colx.analysis.checks import instruction_controls, judge_works, name_control
from colx.analysis.data import SCORES, agent_scores, instruments
from colx.analysis.descriptive import vote_label_share
from colx.analysis.suite import BASELINES, instrument_tests, vs_baselines
from colx.analysis.summary import MEANINGS, primary_family, reading

LENS_TOKENS = {"raw": "lens_tokens.parquet", "rel": "filtered/lens_tokens_words_relative.parquet"}


def all_tests(
    table: pd.DataFrame, n_boot: int, n_perm: int, log=print
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tests for every lens and baseline instrument x score, plus lens-vs-baseline comparisons."""
    keys = [k for k in instruments(table) if k[0] in ("lens", *BASELINES)]
    records, run_tables = [], []
    for score in SCORES:
        runs_by_key = {}
        for key in keys:
            recs, runs = instrument_tests(table, key, score, n_boot, n_perm)
            records += recs
            runs_by_key[key] = runs
            run_tables.append(runs.assign(score=score))
            log(f"{score} {key} done")
        bases = {k[0]: r for k, r in runs_by_key.items() if k[0] in BASELINES}
        for key, runs in runs_by_key.items():
            if key[0] == "lens":
                tag = {"judge": "lens", "arm": key[1], "position": key[2], "score": score}
                records += [tag | r for r in vs_baselines(runs, bases, n_boot)]
    return pd.DataFrame(records), pd.concat(run_tables, ignore_index=True)


def readings(tests: pd.DataFrame, primary: pd.DataFrame, checks: pd.DataFrame) -> list[dict]:
    """The plan's result-table reading for each arm x position (score B)."""
    out = []
    for (arm, pos), prim in primary.groupby(["arm", "position"]):
        b_rows = tests[
            (tests.judge == "lens")
            & (tests.arm == arm)
            & (tests.position == pos)
            & (tests.score == "score_B")
        ].set_index("test")
        gate = checks[
            (checks.check == "instruction_control_vote_free")
            & (checks.arm == arm)
            & (checks.position == pos)
        ].passes.item()
        verdicts = prim.set_index("test").verdict
        beats = {
            b: bool(b_rows.loc[f"b_vs_{b}", "beats"]) for b in ("text", "instruction_only", "vote")
        }
        key = reading(gate, verdicts["a"], verdicts["b"], b_rows.loc["b_style", "p"], beats)
        out.append(
            {
                "arm": arm,
                "position": pos,
                "gate": bool(gate),
                "a": verdicts["a"],
                "b": verdicts["b"],
                "b_style_p": float(b_rows.loc["b_style", "p"]),
                **{f"beats_{k}": v for k, v in beats.items()},
                "reading": key,
                "meaning": MEANINGS[key],
            }
        )
    return out


def analyse(out_dir: Path, n_boot: int = 10_000, n_perm: int = 10_000, log=print) -> dict:
    """Run everything; save outputs; return the summary."""
    folder = out_dir / "analysis"
    folder.mkdir(parents=True, exist_ok=True)
    table = agent_scores(out_dir)
    tests, runs = all_tests(table, n_boot, n_perm, log)
    raw_scores = pd.read_parquet(out_dir / "judge" / "scores.parquet")
    checks = pd.DataFrame(
        [
            judge_works(table, n_boot, n_perm),
            *instruction_controls(table, n_boot, n_perm),
            *name_control(raw_scores),
        ]
    )
    primary = primary_family(tests)
    summary = {
        "label": "planned (amendment 1; words-relative arm partly exploratory)",
        "checks": checks.to_dict("records"),
        "primary": primary.to_dict("records"),
        "readings": readings(tests, primary, checks),
    }
    meta = provenance.collect("col lens-judge analyse", n_boot=n_boot, n_perm=n_perm)
    (folder / "aurocs.json").write_text(
        json.dumps(
            meta | {"tests": tests.to_dict("records"), "checks": checks.to_dict("records")},
            indent=1,
            default=str,
        )
    )
    (folder / "summary.json").write_text(json.dumps(meta | summary, indent=1, default=str))
    runs.to_parquet(folder / "run_scores.parquet", index=False)
    agents, run_meta = (
        pd.read_parquet(out_dir / "agents.parquet"),
        pd.read_parquet(out_dir / "runs.parquet"),
    )
    share = pd.concat(
        [
            vote_label_share(pd.read_parquet(out_dir / p), agents, run_meta).assign(arm=a)
            for a, p in LENS_TOKENS.items()
        ]
    )
    share.to_parquet(folder / "vote_label_share.parquet", index=False)
    return summary
