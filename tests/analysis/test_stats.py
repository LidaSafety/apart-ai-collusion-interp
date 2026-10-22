import numpy as np
import pytest

from colx.analysis.stats import (
    auroc,
    bootstrap_ci,
    bootstrap_draws,
    holm,
    paired_diff,
    recall_at_fpr,
    shuffle_p,
    sign_test,
)


def test_auroc_perfect_reversed_and_ties() -> None:
    labels = np.array([1, 1, 0, 0])
    assert auroc(np.array([0.9, 0.8, 0.2, 0.1]), labels) == 1.0
    assert auroc(np.array([0.1, 0.2, 0.8, 0.9]), labels) == 0.0
    assert auroc(np.array([0.5, 0.5, 0.5, 0.5]), labels) == 0.5


def test_auroc_matches_pairwise_count() -> None:
    rng = np.random.default_rng(0)
    s, y = rng.normal(size=30), rng.integers(0, 2, 30)
    pos, neg = s[y == 1], s[y == 0]
    pairs = np.mean([(p > n) + 0.5 * (p == n) for p in pos for n in neg])
    assert auroc(s, y) == pytest.approx(pairs)


def test_bootstrap_draws_keep_both_classes_and_clusters_whole() -> None:
    clusters = np.array([0, 0, 1, 1, 2, 2])
    labels = np.array([1, 0, 0, 0, 1, 0])
    for rows in bootstrap_draws(clusters, labels, np.random.default_rng(0), 50):
        assert labels[rows].any() and not labels[rows].all()
        counts = np.bincount(rows, minlength=6)
        assert all(counts[2 * c] == counts[2 * c + 1] for c in range(3))


def test_bootstrap_ci_brackets_a_clear_signal() -> None:
    rng = np.random.default_rng(0)
    y = np.repeat([1, 0], 30)
    s = y + rng.normal(scale=0.5, size=60)
    draws = bootstrap_draws(np.arange(60), y, rng, 300)
    lo, hi = bootstrap_ci(lambda r: auroc(s[r], y[r]), draws)
    assert 0.5 < lo < auroc(s, y) < hi <= 1.0


def test_shuffle_p_small_for_signal_large_for_noise() -> None:
    rng = np.random.default_rng(0)
    y = np.repeat([1, 0], 20)
    plain = np.zeros(40, dtype=int)
    assert shuffle_p(y + rng.normal(scale=0.3, size=40), y, plain, rng, 500) < 0.01
    interleaved = np.arange(40.0)  # positives and negatives alternate: AUROC ~ 0.5
    assert shuffle_p(interleaved, np.arange(40) % 2, plain, rng, 500) > 0.3


def test_shuffle_within_groups_keeps_group_label_counts() -> None:
    # One positive per group: shuffling within groups can only move it inside its group.
    y = np.array([1, 0, 1, 0])
    s = np.array([1.0, 0.0, 1.0, 0.0])
    p = shuffle_p(s, y, np.array([0, 0, 1, 1]), np.random.default_rng(0), 400)
    assert p == pytest.approx(0.25, abs=0.07)  # 1 of 4 equally likely layouts is perfect


def test_paired_diff() -> None:
    draws = [np.array([0])] * 10
    out = paired_diff(lambda r: 0.8, lambda r: 0.6, draws)
    assert out["lower_95"] == pytest.approx(0.2) and out["p"] == 0.0


def test_holm() -> None:
    assert holm({"a": 0.01, "b": 0.04, "c": 0.03}) == {"a": True, "c": False, "b": False}
    assert holm({"a": 0.01, "b": 0.02}) == {"a": True, "b": True}


def test_sign_test() -> None:
    assert sign_test(5, 0) == pytest.approx(1 / 32)
    assert sign_test(4, 1) == pytest.approx(6 / 32)


def test_recall_at_fpr() -> None:
    s = np.array([0.9, 0.8, 0.7, 0.6, 0.95, 0.5, 0.4])
    y = np.array([1, 1, 1, 1, 0, 0, 0])
    out = recall_at_fpr(s, y, max_false=1)
    assert out["false_flags"] <= 1 and out["recall"] == 1.0
