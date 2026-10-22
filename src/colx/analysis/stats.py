"""Statistics for the round-4 tests: AUROC, cluster bootstrap, label shuffles, Holm, sign test.

All randomness takes an explicit `numpy.random.Generator` (seed 0 in the plan).
- AUROC is the Mann-Whitney statistic (ties count one half).
- Intervals resample whole scenarios (clusters) with replacement; draws that lose a class
  are redrawn, so every interval uses exactly `n_boot` valid draws.
- Shuffle p-values are one-sided, (1 + #{shuffled ≥ observed}) / (1 + n_perm).
"""

from collections.abc import Callable

import numpy as np
from scipy.stats import binom, rankdata


def auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Probability that a random positive outscores a random negative (ties = 1/2)."""
    labels = labels.astype(bool)
    n_pos, n_neg = labels.sum(), (~labels).sum()
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = rankdata(scores)
    return float((ranks[labels].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def _cluster_index(clusters: np.ndarray) -> list[np.ndarray]:
    """Row indices of each cluster."""
    return [np.flatnonzero(clusters == c) for c in np.unique(clusters)]


def bootstrap_draws(clusters: np.ndarray, labels: np.ndarray, rng, n_boot: int) -> list[np.ndarray]:
    """`n_boot` resamples of whole clusters (row indices), each holding both classes."""
    groups, labels = _cluster_index(clusters), labels.astype(bool)
    draws = []
    while len(draws) < n_boot:
        rows = np.concatenate([groups[g] for g in rng.integers(0, len(groups), len(groups))])
        if labels[rows].any() and not labels[rows].all():
            draws.append(rows)
    return draws


def bootstrap_ci(
    stat: Callable[[np.ndarray], float], draws: list[np.ndarray]
) -> tuple[float, float]:
    """95% percentile interval of `stat(rows)` over the bootstrap draws."""
    values = np.array([stat(rows) for rows in draws])
    return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))


def shuffle_p(
    scores: np.ndarray, labels: np.ndarray, groups: np.ndarray, rng, n_perm: int
) -> float:
    """One-sided p of the AUROC under label shuffles within `groups` (one group = plain)."""
    observed = auroc(scores, labels)
    index = _cluster_index(groups)
    hits = 0
    for _ in range(n_perm):
        shuffled = labels.copy()
        for rows in index:
            shuffled[rows] = labels[rng.permutation(rows)]
        hits += auroc(scores, shuffled) >= observed
    return (1 + hits) / (1 + n_perm)


def paired_diff(stat_a, stat_b, draws: list[np.ndarray]) -> dict[str, float]:
    """Paired bootstrap of stat_a - stat_b: one-sided lower 95% bound and p = P(diff ≤ 0)."""
    diffs = np.array([stat_a(rows) - stat_b(rows) for rows in draws])
    return {"lower_95": float(np.percentile(diffs, 5)), "p": float((diffs <= 0).mean())}


def holm(pvalues: dict[str, float], alpha: float = 0.05) -> dict[str, bool]:
    """Holm step-down: which hypotheses are rejected at family-wise level alpha."""
    order = sorted(pvalues, key=pvalues.get)
    rejected, still = {}, True
    for k, name in enumerate(order):
        still = still and pvalues[name] <= alpha / (len(order) - k)
        rejected[name] = still
    return rejected


def sign_test(wins: int, losses: int) -> float:
    """One-sided sign-test p of at least `wins` successes in wins + losses fair trials."""
    n = wins + losses
    return float(binom.sf(wins - 1, n, 0.5)) if n else float("nan")


def recall_at_fpr(scores: np.ndarray, labels: np.ndarray, max_false: int) -> dict[str, float]:
    """Share of positives caught at the lowest threshold flagging ≤ max_false negatives."""
    labels = labels.astype(bool)
    neg = np.sort(scores[~labels])[::-1]
    threshold = neg[max_false] if len(neg) > max_false else -np.inf
    flagged = scores > threshold
    return {
        "threshold": float(threshold),
        "recall": float(flagged[labels].mean()),
        "false_flags": int(flagged[~labels].sum()),
    }
