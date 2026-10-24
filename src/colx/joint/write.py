"""Run every planned joint-judge test and write `results/joint-judge/analysis/`.

- `tests.json`: every test record per instrument, every comparison, the pair tests;
- `summary.json`: the Holm-corrected primary family (plan "Tests") and the pair tests;
- `run_scores.parquet`: the joint judge's run scores with labels.
Round 4's run scores (score B) come from `results/round4-judge/analysis/run_scores.parquet`.
"""

import json
from pathlib import Path

import pandas as pd

from colx import provenance
from colx.analysis.stats import holm
from colx.joint.suite import compare, instrument_tests, pair_found

LABELS = ["run_id", "scenario_id", "mode", "style_group", "run_colluded"]
ROUND4_BASELINES = ("text", "instruction_only", "vote")


def joint_runs(scores: pd.DataFrame, runs: pd.DataFrame) -> dict[tuple, pd.DataFrame]:
    """Run tables of each joint instrument, keyed by (arm, position); score = rating."""
    labels = runs.rename(columns={"colluded": "run_colluded"})[LABELS]
    return {
        key: g[["run_id", "rating"]].rename(columns={"rating": "run_score"}).merge(labels)
        for key, g in scores.groupby(["arm", "position"])
    }


def round4_runs(round4_dir: Path) -> dict[tuple, pd.DataFrame]:
    """Round 4's run tables (score B), keyed by (judge, arm, position)."""
    table = pd.read_parquet(round4_dir / "analysis" / "run_scores.parquet")
    table = table[table.score == "score_B"]
    return dict(list(table.groupby(["judge", "arm", "position"])))


def comparisons(joint: dict, r4: dict, n_boot: int) -> list[dict]:
    """The plan's paired comparisons (x minus y, AUROC difference)."""
    disc = joint[("discussion", "-")]
    pairs = [("discussion", disc, "round4_text", r4[("text", "-", "-")], ("a", "b"))]
    for pos in ("P1", "P2"):
        lens, both = joint[("lens", pos)], joint[("both", pos)]
        pairs.append((f"both_{pos}", both, "discussion", disc, ("a", "b")))
        pairs.append(
            (f"lens_{pos}", lens, f"round4_rel_{pos}", r4[("lens", "rel", pos)], ("a", "b"))
        )
        for base in ROUND4_BASELINES:
            for name, x in ((f"lens_{pos}", lens), (f"both_{pos}", both)):
                pairs.append((name, x, f"round4_{base}", r4[(base, "-", "-")], ("b",)))
    return [
        {"x": xn, "y": yn} | compare(x, y, test, n_boot)
        for xn, x, yn, y, tests in pairs
        for test in tests
    ]


def primary_family(tests: list[dict], diffs: list[dict]) -> list[dict]:
    """Lens a and b at P1/P2, and both - discussion on b at P1/P2: Holm over 6 tests."""
    rows = {
        f"lens_{t['position']}_{t['test']}": t
        for t in tests
        if t["arm"] == "lens" and t["test"] in ("a", "b")
    }
    rows |= {
        f"{d['x']}_minus_discussion_b": d
        for d in diffs
        if d["y"] == "discussion" and d["test"] == "b"
    }
    rejected = holm({name: r["p"] for name, r in rows.items()})
    return [
        {
            "name": name,
            "p": r["p"],
            "estimate": r.get("auroc", r.get("diff")),
            "ci_low": r.get("ci_low"),
            "ci_high": r.get("ci_high"),
            "lower_95": r.get("lower_95"),
            "holm_rejected": rejected[name],
        }
        for name, r in rows.items()
    ]


def analyse(
    out_dir: Path, round4_dir: Path, n_boot: int = 10_000, n_perm: int = 10_000, log=print
) -> dict:
    """Run everything; save outputs; return the summary."""
    folder = out_dir / "analysis"
    folder.mkdir(parents=True, exist_ok=True)
    scores = pd.read_parquet(out_dir / "scores.parquet")
    runs = pd.read_parquet(round4_dir / "runs.parquet")
    agents = pd.read_parquet(round4_dir / "agents.parquet")
    joint = joint_runs(scores, runs)
    tests = []
    for (arm, pos), table in joint.items():
        tests += [
            {"arm": arm, "position": pos} | t for t in instrument_tests(table, n_boot, n_perm)
        ]
        log(f"{arm} {pos} done")
    diffs = comparisons(joint, round4_runs(round4_dir), n_boot)
    roles = agents.groupby("run_id").apply(lambda g: dict(zip(g.agent, g.role, strict=True)))
    coll = runs[runs["mode"] == "collusion"].set_index("run_id")["colluded"]
    pairs = [
        {"arm": arm, "position": pos} | p
        for (arm, pos), g in scores.groupby(["arm", "position"])
        for p in pair_found(g, roles, coll)
    ]
    summary = {
        "label": "planned (docs/plans/joint-judge.md)",
        "primary": primary_family(tests, diffs),
        "pair_found": pairs,
    }
    meta = provenance.collect("col lens-judge joint analyse", n_boot=n_boot, n_perm=n_perm)
    record = meta | {"tests": tests, "comparisons": diffs, "pair_found": pairs}
    (folder / "tests.json").write_text(json.dumps(record, indent=1, default=str))
    (folder / "summary.json").write_text(json.dumps(meta | summary, indent=1, default=str))
    tables = [t.assign(arm=a, position=p) for (a, p), t in joint.items()]
    pd.concat(tables, ignore_index=True).to_parquet(folder / "run_scores.parquet", index=False)
    return summary
