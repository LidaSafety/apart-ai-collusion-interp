import pandas as pd

from colx.joint.run import format_check


def test_format_check_counts_failures() -> None:
    scores = pd.DataFrame(
        {
            "top_token_text": ["7", " 2", "**"],
            "digit_mass": [0.99, 0.6, 0.1],
            "pair": [[1, 3], None, [2, 4]],
        }
    )
    assert format_check(scores) == {
        "prompts": 3,
        "top token is a digit": 2,
        "P(0..9) >= 0.5": 2,
        "min P(0..9)": 0.1,
        "PAIR line parsed": 2,
    }
