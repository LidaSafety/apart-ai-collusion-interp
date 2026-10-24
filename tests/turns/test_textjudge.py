from colx.turns.textjudge import text_prompt, visible_messages

MSGS = ["[Ann]: a1", "[Bo]: b1", "[Ann]: a2", "[Bo]: b2", "[Bo]: b3", "[Ann]: a3"]


def test_visible_messages_stop_before_the_agents_round_turn() -> None:
    assert visible_messages(MSGS, "Ann", 3) == MSGS[:5]
    assert visible_messages(MSGS, "Bo", 3) == MSGS[:4]


def test_text_prompt_names_the_agent_and_target() -> None:
    text = text_prompt("brief", MSGS[:2], "Ann", "B")
    assert "[Bo]: b1" in text and "Will Ann vote for Option B" in text
    assert text.index("PUBLIC DISCUSSION") < text.index("Will Ann")
