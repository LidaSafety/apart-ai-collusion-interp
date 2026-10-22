"""Descriptive measure: where the upcoming vote becomes visible in the lens tokens.

Per arm, position and layer: the share of agents whose top-25 contains the label of the
option they then vote for (e.g. "B" or "2", leading space ignored) and not the other label.
"""

import pandas as pd


def vote_label_share(
    tokens: pd.DataFrame, agents: pd.DataFrame, runs: pd.DataFrame
) -> pd.DataFrame:
    """Share of agents showing their own vote label only, per position and layer."""
    labels = runs.set_index("run_id").option_labels.str.split("/")
    votes = agents.set_index(["run_id", "agent_index"]).vote
    shown = (
        tokens.assign(text=tokens.token.str.strip())
        .groupby(["position", "layer", "run_id", "agent_index"])["text"]
        .apply(set)
    )
    rows = []
    for (pos, layer, run_id, idx), texts in shown.items():
        own = votes[(run_id, idx)]
        other = next(label for label in labels[run_id] if label != own)
        rows.append(
            {"position": pos, "layer": layer, "shows_own_vote": own in texts and other not in texts}
        )
    return pd.DataFrame(rows).groupby(["position", "layer"]).shows_own_vote.mean().reset_index()
