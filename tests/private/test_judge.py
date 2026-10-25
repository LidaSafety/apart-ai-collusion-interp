from colx.private.judge import seen_private


def test_seen_private_stops_at_the_agents_own_message() -> None:
    messages = ["[Ann]: plan", "[Bo]: agreed"]
    assert seen_private(messages, "Ann") == ["[Ann]: plan"]
    assert seen_private(messages, "Bo") == messages
