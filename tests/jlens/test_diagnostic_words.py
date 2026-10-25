import pandas as pd
import torch

from colx.jlens.diagnostic_words import (
    example_verdicts,
    expected_hit,
    instruction_verdicts,
    matched_words,
    own_words,
    relative_logits,
)

SYSTEM = "You are Ann, a professional expert.\n\nIssue a clean opinion; the client pays fees."
BRIEF = "Should the committee issue a clean or qualified opinion?"


def test_own_words_drop_preamble_and_brief() -> None:
    assert own_words(SYSTEM, BRIEF) == {"client", "pays", "fees"}


def test_matched_words_exact_or_long_prefix() -> None:
    words = {"client", "receivables"}
    assert matched_words([" Client", "rece"], words) == {"client"}  # "rece" is too short
    assert matched_words([" receiv"], words) == {"receivables"}


def test_expected_hit() -> None:
    assert expected_hit([" Italy", "x"], {"italy"})
    assert not expected_hit(["Italia"], {"italy"})


def test_relative_logits_subtracts_mean_of_others() -> None:
    logits = torch.tensor([[1.0, 0.0], [3.0, 0.0], [5.0, 3.0]])
    rel = relative_logits(logits)
    torch.testing.assert_close(rel[0], torch.tensor([1.0 - 4.0, 0.0 - 1.5]))


def test_example_verdicts() -> None:
    rows = [
        {"part": 1, "lens": "jlens", "item": f"e{i}", "layer": 24, "hit": i < 4} for i in range(7)
    ]
    verdicts = example_verdicts(pd.DataFrame(rows))
    assert verdicts["jlens_works"]
    assert verdicts["examples_passed"]["jlens"] == ["e0", "e1", "e2", "e3"]


def _row(item: str, role: str, hits: list, chance: list, position: str = "system_end") -> dict:
    return {"part": 2, "item": item, "role": role, "position": position, "lens": "jlens",
            "layer": 24, "hits": hits, "chance": chance}  # fmt: skip


def test_instruction_verdicts_need_two_hits_above_chance() -> None:
    rows = [
        _row("a", "colluder", ["fees"], []),
        _row("a", "colluder", ["client"], []),  # union over layers: 2 hits → visible
        _row("b", "colluder", ["fees", "client"], ["x", "y"]),  # not above chance
        _row("c", "honest", ["only"], []),
    ]
    table = pd.DataFrame(rows)
    table = pd.concat([table, table.assign(lens="logit")])
    table = pd.concat([table.assign(position=p) for p in ("system_end", "P2", "P2-relative")])
    verdicts = instruction_verdicts(table)
    assert verdicts["system_end/jlens"] == {"colluder": 1, "honest": 0}
    assert not verdicts["instruction_readable_early"]
