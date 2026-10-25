from pathlib import Path

import pytest

from colx.narcbench.runs import (
    join_final_prompt,
    load_run,
    load_runs,
    split_final_prompt,
    system_prompts_constant,
)


def test_load_runs_reads_final_calls(core_dir: Path) -> None:
    runs = load_runs(core_dir)
    assert [r.mode for r in runs] == ["collusion", "control"]
    collusion = runs[0]
    assert [a.name for a in collusion.agents] == ["Ann", "Bo", "Cy", "Di"]
    assert collusion.agents[0].role == "colluder"
    assert collusion.agents[1].style == "lowkey"
    assert collusion.target_option == "B"


def test_split_final_prompt_recovers_parts(core_dir: Path) -> None:
    run = load_run(core_dir / "dom__s1__collusion")
    parts = split_final_prompt(run.final_user_prompt, run.public_messages)
    assert parts.brief.endswith("Option B: y")
    assert parts.discussion.startswith("[Ann]:") and parts.discussion.endswith("fine.")
    assert parts.request.startswith("The committee votes.")


def test_split_final_prompt_rejects_other_layout() -> None:
    with pytest.raises(ValueError):
        split_final_prompt("no discussion header here", ("[Ann]: hi",))


def test_system_prompts_constant(core_dir: Path) -> None:
    assert system_prompts_constant(core_dir / "dom__s1__control")


def test_join_final_prompt_inverts_split(core_dir: Path) -> None:
    run = load_run(core_dir / "dom__s1__collusion")
    parts = split_final_prompt(run.final_user_prompt, run.public_messages)
    rebuilt = join_final_prompt(parts.brief, parts.discussion, parts.request)
    assert rebuilt == run.final_user_prompt
