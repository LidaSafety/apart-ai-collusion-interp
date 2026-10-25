import pandas as pd

from colx.overlap import text
from colx.overlap.compare import lens_scores, score_table


def test_agent_text_keeps_own_messages_and_drops_names() -> None:
    msgs = [
        "[Ann Lee]: I back Option B, Bob.",
        "[Bob Ray]: Ann Lee is wrong.",
        "[Ann Lee]: Again B.",
    ]
    out = text.agent_text(msgs, "Ann Lee", ["Ann Lee", "Bob Ray"])
    assert "Option B" in out and "Again B." in out
    assert "Bob" not in out and "Ann" not in out and "wrong" not in out


def test_words_drop_stop_words_and_short_tokens() -> None:
    assert text.words("The budget IS over by 5%, an issue.") == ["budget", "issue"]


def test_word_sets_have_words_and_bigrams() -> None:
    sets = text.word_sets("budget overrun risk")
    assert sets["text_words"] == {"budget", "overrun", "risk"}
    assert sets["text_bigrams"] == {("budget", "overrun"), ("overrun", "risk")}


def test_cosine_score_finds_the_similar_pair() -> None:
    _, x = text.top_tfidf(["alpha beta gamma", "delta epsilon", "alpha beta gamma", "zeta eta"])
    score, pair = text.cosine_score(x)
    assert pair == (1, 3) and score > 0.5


def test_top_tfidf_returns_at_most_k_words() -> None:
    tops, _ = text.top_tfidf(["apple pear plum kiwi", "melon lime"], k=2)
    assert all(len(t) <= 2 for t in tops)


def test_lens_scores_find_the_pair_sharing_entries() -> None:
    rows = []
    for agent, ids in {"a": [1, 2, 9], "b": [3, 4], "c": [1, 2, 8], "d": [5, 6]}.items():
        for rendering in ("raw", "rel"):
            rows += [
                {"run_id": "r", "agent": agent, "position": "P1", "layer": 0, "token_id": t,
                 "rendering": rendering}
                for t in ids
            ]  # fmt: skip
    frame = pd.DataFrame({"run_id": ["r"], "order": [["a", "b", "c", "d"]], "colluders": [(1, 3)]})
    scores = lens_scores(pd.DataFrame(rows), frame)
    assert scores["lens_raw"][0] == (2.0, (1, 3))
    table = score_table(scores, frame)
    assert table.pair_found.all() and table.split_found.all()
    assert set(table.instrument) == {"lens_raw", "lens_rel"}
