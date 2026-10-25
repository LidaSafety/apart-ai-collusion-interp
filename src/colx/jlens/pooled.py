"""Pool an agent's words-relative lens tokens over the 10 layers into one list of 25.

The joint judge (docs/plans/joint-judge.md) reads four agents at once, so each agent gets
one short list instead of round 4's 10 lines of 25. Relative scores are not comparable
across layers (median 1.17 at layer 39, 2.34 at layer 58 at P1), so tokens are pooled by
their within-layer rank, not their score:
- a token's text is stripped of spaces, so "␣secretly" and "secretly" are one entry;
- digit-only tokens are dropped: the judge answers with a digit and the agents are
  numbered 1-4, and digits fill a median of 3 of the 25 slots at P1 (up to 10);
- each entry keeps its best rank over the layers and the number of layers it appears in;
- entries are ordered by best rank, then more layers, then earliest layer, then text, and
  the first 25 are kept.
"""

import pandas as pd

POOLED_K = 25
KEYS = ["run_id", "agent_index", "agent", "position"]


def pooled_tokens(rows: pd.DataFrame, k: int = POOLED_K) -> list[tuple[str, int]]:
    """One agent's pooled list at one position: (token text, number of layers), best first."""
    rows = rows.assign(text=rows["token"].str.strip())
    entries = (
        rows[~rows["text"].str.isdigit()]
        .groupby("text")
        .agg(best_rank=("rank", "min"), n_layers=("layer", "nunique"), first=("layer", "min"))
        .reset_index()
        .sort_values(["best_rank", "n_layers", "first", "text"], ascending=[1, 0, 1, 1])
        .head(k)
    )
    return list(zip(entries["text"], entries["n_layers"].astype(int), strict=True))


def render_pooled(tokens: list[tuple[str, int]]) -> str:
    """Comma-separated tokens, with "(N layers)" after a token found in N > 1 layers."""
    return ", ".join(text if n == 1 else f"{text} ({n} layers)" for text, n in tokens)


def pooled_table(words_relative: pd.DataFrame, k: int = POOLED_K) -> pd.DataFrame:
    """The rendered pooled list of every (run, agent, position)."""
    rows = [
        dict(zip(KEYS, key, strict=True)) | {"pooled": render_pooled(pooled_tokens(group, k))}
        for key, group in words_relative.groupby(KEYS, sort=True)
    ]
    return pd.DataFrame(rows)
