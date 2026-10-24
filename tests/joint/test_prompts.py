from colx.joint.prompts import QUESTION, joint_prompt

NAMES = ["Cy", "Ann", "Di", "Bo"]
POOLED = ["secret (2 layers), plan", "audit", "fees", "risk"]


def test_lens_arm_numbers_agents_without_names_or_discussion() -> None:
    text = joint_prompt("lens", "brief", NAMES, "[Ann]: hi", POOLED, "P1")
    assert "Agent 1: secret (2 layers), plan" in text and "Agent 4: risk" in text
    assert "Ann" not in text and "PUBLIC DISCUSSION" not in text
    assert "just before the agent writes its vote" in text
    assert text.endswith(QUESTION)


def test_discussion_arm_lists_names_and_no_lens() -> None:
    text = joint_prompt("discussion", "brief", NAMES, "[Ann]: hi")
    assert "[Ann]: hi" in text and "Agent 2 (Ann)" in text
    assert "LENS TOKENS" not in text


def test_both_arm_puts_names_on_lens_lines() -> None:
    text = joint_prompt("both", "brief", NAMES, "[Ann]: hi", POOLED, "P2")
    assert "[Ann]: hi" in text and "Agent 1 (Cy): secret (2 layers), plan" in text
    assert "THE AGENTS:" not in text
    assert text.index("PUBLIC DISCUSSION") < text.index("LENS TOKENS")
