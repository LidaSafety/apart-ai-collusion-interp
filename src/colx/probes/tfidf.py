"""Supervised TF-IDF baseline: the text twin of NARCBench's deception probe (amendment 4).

Per agent, the text is its own public discussion messages, with name prefixes and agent
names removed (`overlap.text.agent_text`). A standard `TfidfVectorizer()` and
`LogisticRegression()` are trained colluder vs honest on Core collusion runs (the probe's
training set), and the per-agent score is the decision function. The run statistics are
the probe's: Peak Suspicion, Deception Split, and their Asymmetry classifier.
Validity gate: with colluder labels shuffled within runs the Core score must stay near 0.5.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from colx.narcbench.runs import Run
from colx.overlap.text import agent_text
from colx.probes.analyse import domain_of
from colx.probes.narc import probe_module

MAX_ITER = 1000  # sklearn's default 100 can stop short of convergence on sparse text


def agent_texts(runs: list[Run]) -> dict:
    """{run_id: {"mode", "agents": {name: (role, text)}}} from the public messages."""
    out = {}
    for r in runs:
        names = sorted(a.name for a in r.agents)
        out[r.run_id] = {
            "mode": r.mode,
            "agents": {
                a.name: (a.role, agent_text(list(r.public_messages), a.name, names))
                for a in r.agents
            },
        }
    return out


def _train(core: dict, rids: list[str], shuffle: np.random.RandomState | None):
    """Vectorizer and classifier on the collusion runs among `rids` (labels optionally shuffled)."""
    texts, y = [], []
    for r in rids:
        if core[r]["mode"] != "collusion":
            continue
        agents = sorted(core[r]["agents"].items())
        roles = [role for _, (role, _) in agents]
        if shuffle is not None:
            roles = list(shuffle.permutation(roles))
        texts += [t for _, (_, t) in agents]
        y += [role == "colluder" for role in roles]
    vec = TfidfVectorizer()
    clf = LogisticRegression(max_iter=MAX_ITER).fit(vec.fit_transform(texts), y)
    return vec, clf


def _stats(runs: dict, rids: list[str], vec, clf) -> dict:
    """Per-run Peak, Split and Asymmetry features from per-agent decision scores."""
    peak, split, asym = [], [], []
    for r in rids:
        s = clf.decision_function(vec.transform([t for _, t in runs[r]["agents"].values()]))
        top = np.sort(s)[::-1]
        peak.append(top[0])
        split.append(top[:2].mean() - top[2:].mean())
        asym.append([np.var(s), top[0] - top[-1], top[:2].mean() - top[2:].mean(), s.mean()])
    return {"peak_suspicion": np.array(peak), "deception_split": np.array(split),
            "asymmetry_probe": np.array(asym)}  # fmt: skip


def _score(core: dict, train_rids: list, sets: dict, shuffle=None) -> dict:
    """Train on `train_rids`; score every (name, run_ids) in `sets` with all three methods."""
    rl = probe_module()
    vec, clf = _train(core, train_rids, shuffle)
    train = _stats(core, train_rids, vec, clf)
    y = np.array([core[r]["mode"] == "collusion" for r in train_rids], int)
    fs, asym = rl._train_asymmetry_classifier(train, y)
    out = {}
    for name, (runs, rids) in sets.items():
        st = _stats(runs, rids, vec, clf)
        st["asymmetry_probe"] = asym.predict_proba(fs.transform(st["asymmetry_probe"]))[:, 1]
        for i, r in enumerate(rids):
            out[(name, r)] = {m: float(v[i]) for m, v in st.items()}
    return out


def heldout_scores(core: dict, extras: dict, shuffle_seed: int | None = None) -> dict:
    """Leave-one-domain-out: per Core domain, score that domain's Core and extra-set runs."""
    shuffle = None if shuffle_seed is None else np.random.RandomState(shuffle_seed)
    out = {}
    for d in sorted({domain_of(r) for r in core}):
        train = sorted(r for r in core if domain_of(r) != d)
        sets = {"core": (core, sorted(r for r in core if domain_of(r) == d))}
        sets |= {
            n: (runs, sorted(r for r in runs if domain_of(r) == d)) for n, runs in extras.items()
        }
        out |= _score(core, train, {k: v for k, v in sets.items() if v[1]}, shuffle)
    return out


def global_scores(core: dict, extras: dict) -> dict:
    """Train on all of Core; score every run of the extra sets (the Transfer protocol)."""
    return _score(core, sorted(core), {n: (runs, sorted(runs)) for n, runs in extras.items()})
