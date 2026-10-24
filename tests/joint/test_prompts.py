from colx.joint.prompts import QUESTION, joint_prompt

NAMES = ["Cy", "Ann", "Di", "Bo"]
POOLED = ["secret (2 layers), plan", "audit", "fees", "risk"]
GRIDS = [f"Layer 24: tok{i}\nLayer 28: more{i}" for i in range(4)]


def test_pooled_arm_one_line_per_numbered_agent_without_names() -> None:
    text = joint_prompt("lens_pooled", "brief", NAMES, "[Ann]: hi", POOLED, "P1")
    assert "Agent 1: secret (2 layers), plan" in text and "Agent 4: risk" in text
    assert "Ann" not in text and "PUBLIC DISCUSSION" not in text
    assert "just before the agent writes its vote" in text and "pooled over 10 layers" in text
    assert text.endswith(QUESTION)


def test_grid_arms_put_each_grid_under_its_agent() -> None:
    rel = joint_prompt("lens_rel", "brief", NAMES, "[Ann]: hi", GRIDS, "P2")
    assert "Agent 1:\nLayer 24: tok0\nLayer 28: more0" in rel
    assert "compared with the average agent" in rel and "␣" not in rel
    raw = joint_prompt("lens_raw", "brief", NAMES, "[Ann]: hi", GRIDS, "P1")
    assert "25 tokens most active there" in raw and "␣" in raw


def test_discussion_arm_lists_names_and_no_lens() -> None:
    text = joint_prompt("discussion", "brief", NAMES, "[Ann]: hi")
    assert "[Ann]: hi" in text and "Agent 2 (Ann)" in text
    assert "LENS TOKENS" not in text


def test_both_arm_puts_names_on_the_words_relative_grids() -> None:
    text = joint_prompt("both", "brief", NAMES, "[Ann]: hi", GRIDS, "P2")
    assert "[Ann]: hi" in text and "Agent 1 (Cy):\nLayer 24: tok0" in text
    assert "THE AGENTS:" not in text and "compared with the average agent" in text
    assert text.index("PUBLIC DISCUSSION") < text.index("LENS TOKENS")
