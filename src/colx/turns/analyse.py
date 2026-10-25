"""The planned discussion-turn tests (plan: docs/plans/discussion-turns.md, "Tests").

Per read point (round 1-3 x T-start/T-end):
- held-out lens classifiers (words-relative primary, raw secondary) for follow-through
  among the 100 colluders: AUROC, scenario bootstrap, plain and within-style shuffles,
  the split-run sign test, and paired differences against the style and text baselines;
- the run-level token-overlap score (joint-judge follow-up A), test b.
Primary family: the words-relative classifier at the 6 read points, Holm.
"""

import numpy as np
import pandas as pd

from colx.analysis.stats import auroc, bootstrap_draws, holm, paired_diff, sign_test
from colx.analysis.suite import auroc_test
from colx.joint.pairs import overlap_score
from colx.turns import classify
from colx.turns.stored import TURN_POSITIONS


def split_runs(colluders: pd.DataFrame, scores: np.ndarray) -> dict:
    """Runs with one follower and one non-follower: does the follower score higher?"""
    wins = losses = 0
    for _, pair in colluders.assign(score=scores).groupby("run_id"):
        if pair.voted_target.sum() != 1:
            continue
        follower = pair[pair.voted_target].score.item()
        other = pair[~pair.voted_target].score.item()
        wins, losses = wins + (follower > other), losses + (follower < other)
    return {"wins": wins, "losses": losses, "p": sign_test(wins, losses)}


def versus(scores: np.ndarray, base: np.ndarray, y: np.ndarray, clusters, n_boot: int) -> dict:
    """AUROC of scores minus base: estimate, one-sided lower 95% bound and p."""
    draws = bootstrap_draws(np.asarray(clusters), y, np.random.default_rng(0), n_boot)
    diff = paired_diff(lambda r: auroc(scores[r], y[r]), lambda r: auroc(base[r], y[r]), draws)
    return {"diff": auroc(scores, y) - auroc(base, y), **diff, "beats": diff["lower_95"] > 0}


def classifier_tests(
    colluders: pd.DataFrame, scores: np.ndarray, baselines: dict, n_boot: int, n_perm: int
) -> list[dict]:
    """All colluder-level tests of one set of held-out scores."""
    y = colluders.voted_target.to_numpy(bool)
    scen, plain = colluders.scenario_id.to_numpy(), np.zeros(len(y), int)
    out = [
        {"test": "follow_through"} | auroc_test(scores, y, scen, plain, n_boot, n_perm),
        {"test": "within_style"} | auroc_test(scores, y, scen, colluders["style"], n_boot, n_perm),
        {"test": "split_runs"} | split_runs(colluders, scores),
    ]
    return out + [
        {"test": f"minus_{name}"} | versus(scores, b, y, scen, n_boot)
        for name, b in baselines.items()
    ]


def overlap_test_b(
    tokens: pd.DataFrame, runs: pd.DataFrame, agents: pd.DataFrame, n_boot: int, n_perm: int
) -> dict:
    """Token-overlap run score among the 4 agents at one read point; test b (50 runs)."""
    coll = runs[runs["mode"] == "collusion"]
    sets = {
        k: set(zip(g.layer, g.token_id, strict=True))
        for k, g in tokens.groupby(["run_id", "agent"])
    }
    names = agents.groupby("run_id").agent.apply(sorted)
    scores = np.array([overlap_score([sets[(r, n)] for n in names[r]])[0] for r in coll.run_id])
    y, scen = coll.colluded.to_numpy(bool), coll.scenario_id.to_numpy()
    return {"test": "overlap_b"} | auroc_test(
        scores, y, scen, np.zeros(len(y), int), n_boot, n_perm
    )


def read_point_tests(
    tokens, colluders, runs, agents, messages, rnd: int, position: str, n_boot: int, n_perm: int
) -> list[dict]:
    """Every test at one read point (round, position)."""
    y = colluders.voted_target.to_numpy(bool)
    folds = classify.scenario_folds(colluders.scenario_id.to_numpy())
    style = classify.heldout_scores(
        colluders[["style", "style_group"]], y, folds, classify.style_model
    )
    text_in = [
        classify.own_messages(messages[r], a, rnd)
        for r, a in zip(colluders.run_id, colluders.agent, strict=True)
    ]
    text = classify.heldout_scores(text_in, y, folds, classify.text_model)
    here = tokens[(tokens["round"] == rnd) & (tokens.position == position)]
    tag = {"round": rnd, "position": position}
    out = [
        tag
        | {"instrument": "style"}
        | auroc_test(style, y, colluders.scenario_id, np.zeros(len(y), int), n_boot, n_perm),
        tag
        | {"instrument": "text"}
        | auroc_test(text, y, colluders.scenario_id, np.zeros(len(y), int), n_boot, n_perm),
    ]
    for rendering in ("rel", "raw"):
        x = classify.presence_matrix(here[here.rendering == rendering], colluders)
        scores = classify.heldout_scores(x, y, folds, classify.lens_model)
        base = {"style": style, "text": text}
        out += [
            tag | {"instrument": f"lens_{rendering}"} | t
            for t in classifier_tests(colluders, scores, base, n_boot, n_perm)
        ]
    rel = here[here.rendering == "rel"]
    overlap = overlap_test_b(rel, runs, agents, n_boot, n_perm)
    return [*out, tag | {"instrument": "overlap_rel"} | overlap]


def all_tests(
    tokens, colluders, runs, agents, messages, n_boot: int, n_perm: int, log=print
) -> tuple[list[dict], list[dict]]:
    """Tests at all 6 read points, and the Holm-corrected primary family."""
    records = []
    for rnd in (1, 2, 3):
        for position in TURN_POSITIONS:
            records += read_point_tests(
                tokens, colluders, runs, agents, messages, rnd, position, n_boot, n_perm
            )
            log(f"round {rnd} {position} done")
    primary = [
        r for r in records if r["instrument"] == "lens_rel" and r["test"] == "follow_through"
    ]
    rejected = holm({f"r{r['round']}_{r['position']}": r["p"] for r in primary})
    family = [
        {
            "name": f"r{r['round']}_{r['position']}",
            "auroc": r["auroc"],
            "ci_low": r["ci_low"],
            "ci_high": r["ci_high"],
            "p": r["p"],
            "holm_rejected": rejected[f"r{r['round']}_{r['position']}"],
        }
        for r in primary
    ]
    return records, family
