import pytest

from colx.gemma.calls import run_calls, strip_name


def _call(name, phase, rnd, role="honest"):
    return {
        "agent_name": name,
        "role": role,
        "phase": phase,
        "round": str(rnd),
        "system_prompt": f"sys {name}",
        "user_prompt": f"{phase} {rnd}",
    }


RESULTS = {
    "private_messages": ["[Ann]: plan a", "[Bo]: plan b"],
    "public_messages": ["[Ann]: r1", "[Bo]: r1b", "[Bo]: r2b", "[Ann]: r2"],
    "final_texts": {"Ann": "RECOMMENDATION: Option A", "Bo": "RECOMMENDATION: Option B"},
}


def test_run_calls_match_each_call_to_its_reply() -> None:
    prompts = [
        _call("Ann", "private", 0, "colluder"),
        _call("Bo", "private", 0, "colluder"),
        _call("Ann", "discussion", 1),
        _call("Bo", "discussion", 1),
        _call("Bo", "discussion", 2),
        _call("Ann", "discussion", 2),
        _call("Ann", "final", 4),
        _call("Bo", "final", 4),
    ]
    calls = run_calls(prompts, RESULTS)
    replies = [(c["agent"], c["phase"], c["round"], c["reply"]) for c in calls]
    assert replies[0] == ("Ann", "private", 0, "plan a")
    assert replies[5] == ("Ann", "discussion", 2, "r2")
    assert replies[7] == ("Bo", "final", 4, "RECOMMENDATION: Option B")
    assert calls[2]["system"] == "sys Ann"


def test_strip_name_checks_the_prefix() -> None:
    assert strip_name("[Ann]: hi", "Ann") == "hi"
    with pytest.raises(ValueError):
        strip_name("[Bo]: hi", "Ann")
