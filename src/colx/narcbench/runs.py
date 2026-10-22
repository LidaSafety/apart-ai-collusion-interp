"""Load NARCBench Core runs: the round-4 (final) call of each agent and its context.

Each run folder holds `run_config.json`, `results.json` and `agent_prompts.json`. The
lens-judge experiment only needs the final round: every agent gets the same user prompt
(scenario brief, the full public discussion, the request to vote) and its own system prompt.
"""

import json
from dataclasses import dataclass
from pathlib import Path

DISCUSSION_HEADER = "\n\nFULL DISCUSSION HISTORY:\n"


@dataclass(frozen=True)
class Agent:
    """One agent's final-round call and outcome."""

    name: str
    role: str
    style: str
    system_prompt: str
    final_text: str
    vote: str


@dataclass(frozen=True)
class Run:
    """One NARCBench run, reduced to what the round-4 experiment reads."""

    run_id: str
    scenario_id: str
    mode: str
    target_option: str
    option_labels: tuple[str, str]
    final_user_prompt: str
    public_messages: tuple[str, ...]
    private_messages: tuple[str, ...]
    agents: tuple[Agent, ...]


@dataclass(frozen=True)
class FinalPrompt:
    """The round-4 user prompt cut into its three parts."""

    brief: str
    discussion: str
    request: str


def split_final_prompt(user_prompt: str, public_messages: tuple[str, ...]) -> FinalPrompt:
    """Cut the round-4 user prompt into the public brief, the discussion and the request.

    The prompt is `brief + DISCUSSION_HEADER + "\\n".join(messages) + "\\n\\n" + request`;
    the function checks that layout instead of guessing, and raises if it differs.
    """
    brief, sep, rest = user_prompt.partition(DISCUSSION_HEADER)
    discussion = "\n".join(public_messages)
    if not sep or not rest.startswith(discussion + "\n\n"):
        raise ValueError("final user prompt does not follow brief / discussion / request")
    return FinalPrompt(brief=brief, discussion=discussion, request=rest[len(discussion) + 2 :])


def join_final_prompt(brief: str, discussion: str, request: str) -> str:
    """Rebuild the round-4 user prompt from its three parts (inverse of split_final_prompt)."""
    return f"{brief}{DISCUSSION_HEADER}{discussion}\n\n{request}"


def _final_agents(config: dict, results: dict, calls: list[dict]) -> tuple[Agent, ...]:
    """Build the agents from their final-phase calls, in call order."""
    finals = [c for c in calls if c["phase"] == "final"]
    return tuple(
        Agent(
            name=c["agent_name"],
            role=results["roles"][c["agent_name"]],
            style=config["agent_styles"][c["agent_name"]],
            system_prompt=c["system_prompt"],
            final_text=results["final_texts"][c["agent_name"]],
            vote=results["votes"][c["agent_name"]],
        )
        for c in finals
    )


def load_run(run_dir: Path) -> Run:
    """Load one run folder."""
    config = json.loads((run_dir / "run_config.json").read_text())
    results = json.loads((run_dir / "results.json").read_text())
    calls = json.loads((run_dir / "agent_prompts.json").read_text())
    final_prompts = {c["user_prompt"] for c in calls if c["phase"] == "final"}
    if len(final_prompts) != 1:
        raise ValueError(f"{run_dir.name}: agents got different round-4 user prompts")
    return Run(
        run_id=config["run_id"],
        scenario_id=config["scenario_id"],
        mode=config["mode"],
        target_option=config["target_option"],
        option_labels=tuple(config["option_labels"]),
        final_user_prompt=final_prompts.pop(),
        public_messages=tuple(results["public_messages"]),
        private_messages=tuple(results["private_messages"]),
        agents=_final_agents(config, results, calls),
    )


def load_runs(core_dir: Path) -> list[Run]:
    """Load every run folder under `core_dir`, sorted by run id."""
    return [load_run(d) for d in sorted(core_dir.iterdir()) if (d / "run_config.json").exists()]


def system_prompts_constant(run_dir: Path) -> bool:
    """Check that each agent's system prompt is the same in all its calls."""
    calls = json.loads((run_dir / "agent_prompts.json").read_text())
    by_agent: dict[str, set[str]] = {}
    for call in calls:
        by_agent.setdefault(call["agent_name"], set()).add(call["system_prompt"])
    return all(len(prompts) == 1 for prompts in by_agent.values())
