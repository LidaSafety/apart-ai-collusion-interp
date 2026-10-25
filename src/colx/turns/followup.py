"""Follow-up B analysis: lens vs frozen text judge at R3 T-start, and the classifier's features.

- B1: the text judge's AUROC, lens minus text judge (paired scenario bootstrap; words-relative
  primary, raw secondary), split runs, and mean scores per run by the number of followers.
- B2 (exploratory): the classifier refitted on all 100 colluders; its 20 most positive and
  20 most negative (layer, token) weights, with how many followers / non-followers have each.
"""

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix

from colx.analysis.suite import auroc_test
from colx.turns import classify
from colx.turns.analyse import split_runs, versus

READ = {"round": 3, "position": "T-start"}


def lens_scores(tokens: pd.DataFrame, colluders: pd.DataFrame, rendering: str):
    """Held-out lens scores at R3 T-start, the presence matrix, and the colluders' token rows."""
    here = tokens[
        (tokens["round"] == READ["round"])
        & (tokens.position == READ["position"])
        & (tokens.rendering == rendering)
    ]
    keys = set(zip(colluders.run_id, colluders.agent, strict=True))
    here = here[[k in keys for k in zip(here.run_id, here.agent, strict=True)]]
    x = classify.presence_matrix(here, colluders)
    y = colluders.voted_target.to_numpy(bool)
    folds = classify.scenario_folds(colluders.scenario_id.to_numpy())
    return classify.heldout_scores(x, y, folds, classify.lens_model), x, here


def by_followers(colluders: pd.DataFrame, scores: np.ndarray) -> dict[int, float]:
    """Mean score of a run's colluders, by how many of them followed through (0, 1, 2)."""
    runs = (
        colluders.assign(s=scores).groupby("run_id").agg(s=("s", "mean"), n=("voted_target", "sum"))
    )
    return {int(k): round(float(v), 3) for k, v in runs.groupby("n").s.mean().items()}


def compare(
    text: np.ndarray, lens: dict, colluders: pd.DataFrame, n_boot: int, n_perm: int
) -> list:
    """B1 records: text judge alone, lens minus text judge, split runs, per-run means."""
    y, scen = colluders.voted_target.to_numpy(bool), colluders.scenario_id.to_numpy()
    plain = np.zeros(len(y), int)
    out = [
        {"instrument": "text_judge", "test": "follow_through"}
        | auroc_test(text, y, scen, plain, n_boot, n_perm),
        {"instrument": "text_judge", "test": "split_runs"} | split_runs(colluders, text),
        {
            "instrument": "text_judge",
            "test": "by_followers",
            "means": by_followers(colluders, text),
        },
    ]
    for rendering, s in lens.items():
        out += [
            {"instrument": f"lens_{rendering}", "test": "minus_text_judge"}
            | versus(s, text, y, scen, n_boot),
            {
                "instrument": f"lens_{rendering}",
                "test": "by_followers",
                "means": by_followers(colluders, s),
            },
        ]
    return out


def top_features(
    x: csr_matrix, here: pd.DataFrame, colluders: pd.DataFrame, k: int = 20
) -> pd.DataFrame:
    """The k most positive and k most negative weights of the classifier fit on all colluders."""
    y = colluders.voted_target.to_numpy(bool)
    weights = classify.lens_model().fit(x, y).coef_[0]
    keys = sorted(set(zip(here.layer, here.token_id, strict=True)))
    text = dict(zip(zip(here.layer, here.token_id, strict=True), here.token, strict=True))
    dense = x.toarray().astype(bool)
    order = list(np.argsort(weights)[::-1][:k]) + list(np.argsort(weights)[:k])
    return pd.DataFrame(
        [
            {
                "direction": "follows" if weights[j] > 0 else "does not follow",
                "layer": keys[j][0],
                "token": text[keys[j]],
                "weight": round(float(weights[j]), 3),
                "followers": int(dense[y, j].sum()),
                "non_followers": int(dense[~y, j].sum()),
            }
            for j in order
        ]
    )
