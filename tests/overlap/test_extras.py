import pandas as pd

from colx.overlap.extras import coalition_side, run_scores, side_test


def sets_with(shared_pair: tuple[int, int], honest_common: int) -> list[set]:
    """Four agents: a pair with 3 exclusive entries; the other pair shares many more overall."""
    base = [{("own", a)} for a in range(4)]
    i, j = shared_pair
    for e in range(3):
        base[i - 1].add(("secret", e))
        base[j - 1].add(("secret", e))
    others = [k for k in range(1, 5) if k not in shared_pair]
    for e in range(honest_common):
        for k in others:
            base[k - 1].add(("normal", e))
    return base


def test_coalition_side_picks_the_pair_sharing_less_in_total() -> None:
    # honest pair (2, 4) shares 5 entries, more than the colluders' 3, so it is the top pair;
    # the rule then names its complement, the colluders (1, 3)
    assert coalition_side(sets_with((1, 3), 5)) == (1, 3)


def test_coalition_side_names_the_complement_when_it_shares_less() -> None:
    # (1, 3) is the top pair (3 exclusive entries) but the complement shares only 1 in total
    assert coalition_side(sets_with((1, 3), 1)) == (2, 4)


def test_side_test_counts_runs_and_skips_controls() -> None:
    s = sets_with((1, 3), 5)
    names = ["a", "b", "c", "d"]
    sets = {(r, n): s[k] for r in ("r1", "r2") for k, n in enumerate(names)}
    frame = pd.DataFrame(
        {"run_id": ["r1", "r2"], "order": [names, names], "colluders": [(1, 3), None]}
    )
    out = side_test(frame, sets)
    assert out["runs_with_right_split"] == 1 and out["named_right"] == 1


def test_run_scores_match_the_overlap_score() -> None:
    s = sets_with((1, 3), 0)
    names = ["a", "b", "c", "d"]
    frame = pd.DataFrame({"run_id": ["r"], "order": [names]})
    assert run_scores(frame, {("r", n): s[k] for k, n in enumerate(names)})[0] == 3.0
