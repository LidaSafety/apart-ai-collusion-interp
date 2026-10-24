"""Held-out classifiers for follow-through among the colluders (plan: discussion-turns.md).

Every classifier is a logistic regression (C = 0.1, not tuned) scored on held-out
scenarios: 10 folds of whole scenarios, assigned in a seeded random order (seed 0), so a
scenario's two colluders are never split between training and testing.
- lens: presence of each (layer, token) among an agent's top-25 at one read point;
- style: the colluder's instruction style and the run's style group (one-hot);
- text: TF-IDF of the colluder's own public messages up to and including that round.
"""

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

N_FOLDS = 10
C = 0.1


def scenario_folds(scenarios: np.ndarray, n_folds: int = N_FOLDS, seed: int = 0) -> np.ndarray:
    """Fold number per row: scenarios shuffled (seeded), then dealt round-robin."""
    unique = np.unique(scenarios)
    order = np.random.default_rng(seed).permutation(unique)
    fold_of = {s: i % n_folds for i, s in enumerate(order)}
    return np.array([fold_of[s] for s in scenarios])


def heldout_scores(features, labels: np.ndarray, folds: np.ndarray, make_model) -> np.ndarray:
    """P(label) for each row from a model trained on the other folds."""
    scores = np.zeros(len(labels))
    for fold in np.unique(folds):
        test = folds == fold
        model = make_model().fit(_rows(features, ~test), labels[~test])
        scores[test] = model.predict_proba(_rows(features, test))[:, 1]
    return scores


def _rows(features, mask: np.ndarray):
    """Select rows of a matrix, a DataFrame or a list."""
    if isinstance(features, pd.DataFrame):
        return features[mask]
    if isinstance(features, list):
        return [f for f, keep in zip(features, mask, strict=True) if keep]
    return features[np.flatnonzero(mask)]


def presence_matrix(tokens: pd.DataFrame, keys: pd.DataFrame) -> csr_matrix:
    """Rows = `keys` (run_id, agent) in order; columns = (layer, token_id) present in top 25."""
    row_of = {k: i for i, k in enumerate(zip(keys.run_id, keys.agent, strict=True))}
    sub = tokens[[k in row_of for k in zip(tokens.run_id, tokens.agent, strict=True)]]
    columns = {c: j for j, c in enumerate(sorted(set(zip(sub.layer, sub.token_id, strict=True))))}
    rows = [row_of[k] for k in zip(sub.run_id, sub.agent, strict=True)]
    cols = [columns[c] for c in zip(sub.layer, sub.token_id, strict=True)]
    return csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(keys), len(columns)))


def lens_model() -> LogisticRegression:
    """Logistic regression on token presence."""
    return LogisticRegression(C=C, max_iter=5000)


def style_model():
    """One-hot style features, then logistic regression."""
    return make_pipeline(OneHotEncoder(handle_unknown="ignore"), LogisticRegression(C=C))


def text_model():
    """TF-IDF of the agent's messages (fitted on training folds only), then logistic."""
    return make_pipeline(TfidfVectorizer(sublinear_tf=True), LogisticRegression(C=C, max_iter=5000))


def own_messages(public_messages: list[str], name: str, upto_round: int) -> str:
    """The agent's own public messages of rounds 1..upto_round, joined."""
    own = [m for m in public_messages if m.startswith(f"[{name}]:")]
    return "\n".join(own[:upto_round])
