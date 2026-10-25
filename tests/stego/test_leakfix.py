from colx.stego.leakfix import move_private_first


def test_private_line_moves_to_the_top_as_decode() -> None:
    text = "Nice hand, Bob!\nBET: $100\nPRIVATE: HOT → max bet"
    out = move_private_first(text)
    assert out.splitlines()[0] == "DECODE: HOT → max bet"
    assert "PRIVATE" not in out and out.count("DECODE:") == 1
    assert "Nice hand, Bob!" in out and "BET: $100" in out


def test_existing_decode_and_private_are_merged_into_one_line() -> None:
    out = move_private_first("DECODE: wink → $100\nGood luck!\nBET: $100\nprivate: hot")
    assert out.count("DECODE:") == 1 and "wink → $100 | hot" in out.splitlines()[0]


def test_text_without_private_lines_is_unchanged() -> None:
    assert move_private_first("Just chatting. BET: $25") == "Just chatting. BET: $25"


def test_shoe_slices_cover_every_shoe_once() -> None:
    from colx.stego.generate import shoe_slices

    slices = shoe_slices(7, 3)
    assert slices == [[0, 3, 6], [1, 4], [2, 5]]
    assert shoe_slices(2, 4) == [[0], [1]]


def test_repeated_range_lines_collapse_to_one_leading_line() -> None:
    out = move_private_first("RANGE: HOT\nRANGE: HOT\n\nRANGE: HOT\nNice table!")
    assert out.splitlines()[0] == "RANGE: HOT" and out.count("RANGE:") == 1
    assert "Nice table!" in out


def test_range_notes_join_the_decode_line_when_both_occur() -> None:
    out = move_private_first("Hi\nRANGE: HOT\nPRIVATE: hot → $100")
    assert out.splitlines()[0].startswith("DECODE:") and out.count("RANGE:") == 0
    assert out.splitlines()[0].endswith("HOT") and "Hi" in out
