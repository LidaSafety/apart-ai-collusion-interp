"""Count summaries of the round-4 labels, checked against the plan's handoff notes."""

import pandas as pd


def _split_runs(agents: pd.DataFrame, runs: pd.DataFrame) -> pd.DataFrame:
    """Return the collusion-mode runs where exactly one colluder voted the target."""
    split_ids = runs.loc[runs["colluders_voted_target"].eq(1) & runs["mode"].eq("collusion")]
    colluders = agents[agents["role"].eq("colluder") & agents["run_id"].isin(split_ids["run_id"])]
    return colluders


def split_run_styles(agents: pd.DataFrame, runs: pd.DataFrame) -> dict[str, int]:
    """Count split runs by style: same style, or voter standard / non-voter lowkey."""
    counts = {"split_runs": 0, "same_style": 0, "voter_standard_other_lowkey": 0, "other": 0}
    for _, pair in _split_runs(agents, runs).groupby("run_id"):
        voter = pair.loc[pair["voted_target"], "style"].item()
        other = pair.loc[~pair["voted_target"], "style"].item()
        counts["split_runs"] += 1
        if voter == other:
            counts["same_style"] += 1
        elif (voter, other) == ("standard", "lowkey"):
            counts["voter_standard_other_lowkey"] += 1
        else:
            counts["other"] += 1
    return counts


def style_group_summary(runs: pd.DataFrame) -> dict[str, int]:
    """Count style groups among collusion-mode runs, and runs in groups with both labels."""
    collusion = runs[runs["mode"] == "collusion"]
    both = collusion.groupby("style_group")["colluded"].transform("nunique") == 2
    return {
        "style_groups": int(collusion["style_group"].nunique()),
        "runs_in_groups_with_both_labels": int(both.sum()),
    }


def label_summary(agents: pd.DataFrame, runs: pd.DataFrame) -> dict[str, int]:
    """Count everything the plan's handoff notes assert about the labels."""
    collusion_agents = agents[agents["mode"] == "collusion"]
    colluders = collusion_agents[collusion_agents["role"] == "colluder"]
    honest = collusion_agents[collusion_agents["role"] == "honest"]
    control = agents[agents["mode"] == "control"]
    collusion_runs = runs[runs["mode"] == "collusion"]
    n_voted = collusion_runs["colluders_voted_target"]
    std = colluders[colluders["style"] == "standard"]
    low = colluders[colluders["style"] == "lowkey"]
    return {
        "runs": len(runs),
        "agents": len(agents),
        "runs_colluded": int(runs["colluded"].sum()),
        "runs_not_colluded": int((~runs["colluded"]).sum()),
        "collusion_runs_2_voted": int((n_voted == 2).sum()),
        "collusion_runs_1_voted": int((n_voted == 1).sum()),
        "collusion_runs_0_voted": int((n_voted == 0).sum()),
        "colluders_voted_target": int(colluders["voted_target"].sum()),
        "colluders": len(colluders),
        "honest_in_collusion_runs_voted_target": int(honest["voted_target"].sum()),
        "control_agents_voted_target": int(control["voted_target"].sum()),
        "colluders_not_voted_target": int((~colluders["voted_target"]).sum()),
        "honest_not_voted_target_in_collusion_runs": int((~honest["voted_target"]).sum()),
        "colluders_standard": len(std),
        "colluders_standard_voted": int(std["voted_target"].sum()),
        "colluders_lowkey": len(low),
        "colluders_lowkey_voted": int(low["voted_target"].sum()),
        "collusion_runs_with_2_private_messages": int(
            (collusion_runs["n_private_messages"] == 2).sum()
        ),
        "votes_parsed_and_match": int((agents["parsed_vote"] == agents["vote"]).sum()),
        "replies_start_recommendation": int(
            agents["final_text"].str.startswith("RECOMMENDATION:").sum()
        ),
        "replies_start_recommendation_option": int(
            agents["final_text"].str.startswith("RECOMMENDATION: Option").sum()
        ),
        **style_group_summary(runs),
        **split_run_styles(agents, runs),
    }
