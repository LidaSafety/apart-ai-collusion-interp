"""How much the four agents of a run share their top-25 lens tokens (label-free).

All four agents read the same round-4 user prompt; only their system prompts differ. If
their top-25 lists are nearly identical, the lens mostly shows the shared prompt, and there
is little agent-specific content for a judge to use.
"""

from itertools import combinations

import pandas as pd


def pairwise_overlap(token_sets: list[set[int]], k: int) -> float:
    """Mean share of tokens two lists have in common, over all pairs: |A ∩ B| / k."""
    pairs = list(combinations(token_sets, 2))
    return sum(len(a & b) for a, b in pairs) / (k * len(pairs))


def overlap_table(tokens: pd.DataFrame) -> pd.DataFrame:
    """Mean within-run pairwise overlap of the agents' top-k lists, per position and layer."""
    k = int(tokens["rank"].max()) + 1
    per_run = (
        tokens.groupby(["position", "layer", "run_id", "agent_index"])["token_id"]
        .apply(set)
        .groupby(["position", "layer", "run_id"])
        .apply(lambda sets: pairwise_overlap(list(sets), k))
    )
    return per_run.groupby(["position", "layer"]).agg(["mean", "min", "max"]).reset_index()
