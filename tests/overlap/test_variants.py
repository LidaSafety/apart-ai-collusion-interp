import random
import types
from pathlib import Path

from colx.overlap import variants
from colx.overlap.generate import link_controls

TEMPLATE = "You are {agent_name}.\n\n{motive}\n\n{deception_instruction}"
NAMES = [f"Name{i}" for i in range(12)]


def fake_core() -> types.SimpleNamespace:
    """The module-level names of core.py that the wrapper touches."""
    scenario = {
        "id": "s0",
        "collusion_motive": "MOTIVE",
        "deception_instruction": "DECEIVE",
        "lowkey_instruction": "LOWKEY",
        "honest_mandate": "HONEST",
    }
    return types.SimpleNamespace(
        SCENARIOS=[scenario],
        NAME_POOL=NAMES,
        COLLUDER_SYSTEM_A=TEMPLATE,
        COLLUDER_SYSTEM_B=TEMPLATE,
        COLLUDER_DISCUSSION_TEMPLATE="PRIVATE COORDINATION\nDISCUSSION HISTORY:\n{history}",
        DISCUSSION_PROMPT_TEMPLATE="DISCUSSION HISTORY:\n{history}",
        call_vllm=lambda system, user, *a, **k: "REPLY",
    )


PARA = {"s0": {"collusion_motive": "M2", "deception_instruction": "D2", "lowkey_instruction": "L2"}}


def test_para_gives_only_the_second_colluder_the_paraphrase() -> None:
    core = fake_core()
    variants.apply_condition(core, "para", PARA)
    first, second = random.Random(0).sample(NAMES, 4)[:2]
    kw = {"motive": "MOTIVE", "deception_instruction": "DECEIVE"}
    assert core.COLLUDER_SYSTEM_A.format(agent_name=first, **kw).endswith("MOTIVE\n\nDECEIVE")
    assert core.COLLUDER_SYSTEM_A.format(agent_name=second, **kw).endswith("M2\n\nD2")
    assert core.call_vllm("s", "no history") == "REPLY"


def test_independent_cuts_the_private_channel() -> None:
    core = fake_core()
    variants.apply_condition(core, "independent", PARA)
    assert core.COLLUDER_DISCUSSION_TEMPLATE == core.DISCUSSION_PROMPT_TEMPLATE
    assert core.call_vllm("s", "private frame only") == variants.NO_CHANNEL
    assert core.call_vllm("s", "DISCUSSION HISTORY:\n...") == "REPLY"


def test_aware_appends_the_warning_to_both_templates() -> None:
    core = fake_core()
    variants.apply_condition(core, "aware", None)
    out = core.COLLUDER_SYSTEM_B.format(agent_name="X", motive="M", deception_instruction="D")
    assert out.endswith(variants.AWARE)


def test_benign_replaces_motive_and_instructions() -> None:
    core = fake_core()
    variants.apply_condition(core, "benign", None)
    s = core.SCENARIOS[0]
    assert s["collusion_motive"] == variants.BENIGN_NOTE
    assert s["deception_instruction"] == s["lowkey_instruction"] == "HONEST"


def test_option_labels_finds_label_words() -> None:
    assert variants.option_labels("Get Patient B in; not Option 2.") == {"Patient B", "Option 2"}


def test_link_controls_links_only_control_runs(tmp_path: Path) -> None:
    core, cond = tmp_path / "core", tmp_path / "cond"
    for name in ("x__control", "x__collusion", "y__control"):
        (core / name).mkdir(parents=True)
    cond.mkdir()
    assert link_controls(core, cond) == 2
    assert sorted(p.name for p in cond.iterdir()) == ["x__control", "y__control"]


def test_para_keys_on_the_scenario_not_only_the_name() -> None:
    core = fake_core()
    variants.apply_condition(core, "para", PARA)
    second = random.Random(0).sample(NAMES, 4)[1]
    kw = {"motive": "OTHER SCENARIO MOTIVE", "deception_instruction": "DECEIVE"}
    out = core.COLLUDER_SYSTEM_A.format(agent_name=second, **kw)
    assert out.endswith("OTHER SCENARIO MOTIVE\n\nDECEIVE")
