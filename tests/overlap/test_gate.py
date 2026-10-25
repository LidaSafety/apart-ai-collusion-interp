from colx.overlap.gate import bigram_share, check


def test_bigram_share_is_one_for_a_copy_and_zero_for_new_wording() -> None:
    text = "Advocate strongly for the expansion project today"
    assert bigram_share(text, text) == 1.0
    assert bigram_share(text, "Push hard in favour of building more") == 0.0


def test_check_fails_a_paraphrase_that_drops_an_option_label() -> None:
    s = {"id": "s", "collusion_motive": "Back Patient B quietly", "deception_instruction": "x",
         "lowkey_instruction": "y"}  # fmt: skip
    para = {"s": {"collusion_motive": "Support the second patient", "deception_instruction": "z",
                  "lowkey_instruction": "w"}}  # fmt: skip
    rows = {r["field"]: r for r in check([s], para)}
    assert not rows["collusion_motive"]["labels_kept"] and not rows["collusion_motive"]["passes"]
