from colx.overlap.anatomy import all_groups, exclusive_by_layer, membership_counts, run_score

# Four agents; entries are (layer, token). Agents 0 and 2 share two entries nobody else has.
SETS = [
    {(1, "a"), (1, "x"), (2, "y"), (1, "all")},
    {(1, "b"), (2, "h"), (1, "all")},
    {(1, "x"), (2, "y"), (2, "c"), (1, "all")},
    {(2, "h"), (1, "d"), (1, "all")},
]


def test_membership_counts_groups_entries_by_their_exact_holders() -> None:
    counts = membership_counts(SETS)
    assert counts[(0, 2)] == 2  # x and y
    assert counts[(1, 3)] == 1  # h
    assert counts[(0, 1, 2, 3)] == 1  # all
    assert counts[(0,)] == 1 and counts[(2,)] == 1


def test_all_groups_lists_singles_then_pairs_then_larger() -> None:
    groups = all_groups(4)
    assert len(groups) == 15
    assert groups[:4] == [(0,), (1,), (2,), (3,)]
    assert groups[4:10] == [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    assert groups[-1] == (0, 1, 2, 3)


def test_run_score_is_largest_pair_count_minus_median() -> None:
    pairs, score = run_score(SETS)
    assert pairs == [0, 2, 0, 0, 1, 0]
    assert score == 2.0


def test_exclusive_by_layer_counts_only_entries_no_other_agent_holds() -> None:
    assert exclusive_by_layer(SETS, (0, 2), [1, 2]) == [1, 1]
    assert exclusive_by_layer(SETS, (1, 3), [1, 2]) == [0, 1]
