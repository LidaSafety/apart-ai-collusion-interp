import pytest

from colx.gemma.extract import p2_index


def test_p2_index_finds_the_token_ending_the_last_message() -> None:
    text = "intro [Bo]: last words. Now vote."
    offsets = [(0, 5), (5, 11), (11, 16), (16, 23), (23, 27), (27, 33)]
    assert p2_index(offsets, text, "[Bo]: last words.") == 3


def test_p2_index_needs_the_message() -> None:
    with pytest.raises(ValueError):
        p2_index([(0, 3)], "abc", "zzz")
