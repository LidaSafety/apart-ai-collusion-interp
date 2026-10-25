"""Amendment 4: NARCBench's deception probes, scored with their own functions.

Two outputs:
- `paper_metrics`: their protocol and aggregation, for the reproduction check. Core uses
  leave-one-domain-out with per-fold AUROC averaged (`held_out_cv_layer`); Transfer
  trains on all of Core and reports AUROC per scenario family and its mean; all are
  averaged over the layer band and seeds 0-9.
- `heldout_run_scores`: one score per run and statistic for paired comparisons with the
  overlap monitor. Every scored run is held out from its probe: per Core domain, the probe
  and run-level classifiers are trained on the other domains and score that domain's Core
  runs and the same domain's runs in every extra set (final calls). Scores are averaged
  over layers and seeds.
"""

import numpy as np
from joblib import Parallel, delayed
from sklearn.metrics import roc_auc_score
from threadpoolctl import threadpool_limits

from colx.probes.narc import probe_module

METHODS = ("peak_suspicion", "deception_split", "activation_alignment", "asymmetry_probe",
           "sorted_concat")  # fmt: skip
SEEDS = range(10)
N_JOBS = 50  # parallel (layer, seed[, domain]) jobs; each is single-process sklearn work
THREADS = 4  # BLAS threads per job, so 50 jobs don't oversubscribe the machine


def _run(fn, augment: bool, *args):
    """Run one job in a worker with NARCBench's augmentation switch set there too.

    Workers import NARCBench's module afresh, so the switch the parent set would not
    reach them; it is set again here before calling their functions.
    """
    probe_module().AUG_ENABLED = augment
    with threadpool_limits(THREADS):
        return fn(*args)


def _parallel(fn, jobs: list[tuple]) -> list:
    """Map `fn` over argument tuples in parallel, keeping the parent's augmentation switch."""
    augment = probe_module().AUG_ENABLED
    return Parallel(n_jobs=N_JOBS)(delayed(_run)(fn, augment, *a) for a in jobs)


def domain_of(run_id: str) -> str:
    """Their domain parsing: 'deception__audit_01__collusion' -> 'audit'."""
    rl = probe_module()
    return rl._domain_from_scenario_id(rl._parse_run_id(run_id)[1])


def _transfer_layer(core: tuple, transfer: tuple, layer: int, seed: int) -> dict:
    """Their Transfer protocol for one layer and seed: AUROC per family, plus pooled."""
    rl = probe_module()
    (cm, cn), (tm, tn) = core, transfer
    scaler, w = rl.train_deception_probe(cm, cn, layer, seed=seed)
    cg = rl.build_groups(cm, cn, layer, phase="discussion", avg_rounds=True)
    crids = sorted(cg)
    cs = rl.compute_scores(cg, crids, scaler, w)
    tg = rl.build_groups(tm, tn, layer, phase="final", avg_rounds=False)
    trids = sorted(tg)
    ts = rl.compute_scores(tg, trids, scaler, w)
    scores = _final_scores(cs, rl._run_labels(cg, crids), ts)
    y = rl._run_labels(tg, trids)
    fam = np.array([tg[r]["scenario"] for r in trids])
    out = {"pooled": {m: roc_auc_score(y, scores[m]) for m in METHODS}}
    for f in sorted(set(fam)):
        mask = fam == f
        if len(np.unique(y[mask])) == 2:
            out[f] = {m: roc_auc_score(y[mask], scores[m][mask]) for m in METHODS}
    return out


def _final_scores(train_scores: dict, train_y: np.ndarray, test_scores: dict) -> dict:
    """Per-run scores of all five methods; the two classifiers are fit on `train_scores`."""
    rl = probe_module()
    fs, clf = rl._train_asymmetry_classifier(train_scores, train_y)
    pca, fs2, clf2 = rl._train_concat_classifier(train_scores, train_y)
    out = {m: np.asarray(test_scores[m]) for m in ("peak_suspicion", "deception_split",
                                                 "activation_alignment")}  # fmt: skip
    out["asymmetry_probe"] = clf.predict_proba(fs.transform(test_scores["asymmetry_probe"]))[:, 1]
    x = fs2.transform(pca.transform(test_scores["sorted_concat"]))
    out["sorted_concat"] = clf2.predict_proba(x)[:, 1]
    return out


def _mean_over(results: list[dict], key: str) -> dict:
    """Mean AUROC per method of one family over the layer x seed results that have it."""
    return {m: float(np.mean([r[key][m] for r in results if key in r])) for m in METHODS}


def _core_cv(core: tuple, layer: int, seed: int) -> dict:
    """Their leave-domain-out Core metrics for one layer and seed."""
    return probe_module().held_out_cv_layer(core[0], core[1], layer, seed=seed)


def paper_metrics(core: tuple, layers: list[int], transfer: tuple | None = None, log=print) -> dict:
    """Their reported numbers: Core held-out (per-fold mean) and Transfer, layer x seed means."""
    jobs = [(core, layer, seed) for layer in layers for seed in SEEDS]
    core_cv = _parallel(_core_cv, jobs)
    log(f"  core: {len(core_cv)} layer x seed runs done")
    out = {"core_heldout": {m: float(np.nanmean([c[m] for c in core_cv])) for m in METHODS}}
    if transfer is not None:
        trans = _parallel(_transfer_layer, [(core, transfer, la, se) for _, la, se in jobs])
        log(f"  transfer: {len(trans)} layer x seed runs done")
        keys = trans[0].keys()
        out["transfer"] = {k: _mean_over(trans, k) for k in keys}
        fams = [k for k in keys if k != "pooled"]
        out["transfer"]["family_mean"] = {
            m: float(np.mean([out["transfer"][f][m] for f in fams])) for m in METHODS
        }
    return out


def _fold(core: tuple, extras: dict, layer: int, seed: int, domain: str, phase: str) -> dict:
    """One held-out domain: {(set, run_id): {method: score}} for that domain's runs."""
    rl = probe_module()
    cm, cn = core
    scaler, w = rl.train_deception_probe(cm, cn, layer, exclude_domain=domain, seed=seed)
    cg = rl.build_groups(cm, cn, layer, phase="discussion", avg_rounds=True)
    tr = sorted(r for r in cg if cg[r]["domain"] != domain)
    train = rl.compute_scores(cg, tr, scaler, w)
    out = {}
    sets = {"core": core} | extras
    for name, (m, n) in sets.items():
        avg = phase == "discussion" and name == "core"
        g = rl.build_groups(m, n, layer, phase=phase if name == "core" else "final", avg_rounds=avg)
        te = sorted(r for r in g if g[r]["domain"] == domain)
        if not te:
            continue
        s = _final_scores(train, rl._run_labels(cg, tr), rl.compute_scores(g, te, scaler, w))
        for i, r in enumerate(te):
            out[(name, r)] = {meth: float(s[meth][i]) for meth in METHODS}
    return out


def _average(results: list[dict]) -> dict:
    """Average per-run method scores over many jobs' {(set, run): {method: score}}."""
    acc: dict = {}
    for res in results:
        for key, vals in res.items():
            for meth, v in vals.items():
                acc.setdefault(key, {}).setdefault(meth, []).append(v)
    return {k: {m: float(np.mean(v)) for m, v in d.items()} for k, d in acc.items()}


def heldout_run_scores(core: tuple, extras: dict, layers: list[int], phase: str, log=print) -> dict:
    """Held-out per-run scores for Core and every extra set, averaged over layers and seeds.

    `phase` is where Core runs are read: "discussion" (their Core protocol, rounds 1-3
    averaged) or "final" (the Transfer protocol, matching the extra sets).
    """
    domains = sorted({domain_of(m["run_id"]) for m in core[0]})
    jobs = [(core, extras, la, se, d, phase) for la in layers for se in SEEDS for d in domains]
    out = _average(_parallel(_fold, jobs))
    log(f"  {len(jobs)} held-out folds done")
    return out


def _global_job(core: tuple, extras: dict, layer: int, seed: int) -> dict:
    """One layer and seed of the Transfer protocol: per-run scores of the extra sets."""
    rl = probe_module()
    scaler, w = rl.train_deception_probe(core[0], core[1], layer, seed=seed)
    cg = rl.build_groups(core[0], core[1], layer, phase="discussion", avg_rounds=True)
    cr = sorted(cg)
    train = rl.compute_scores(cg, cr, scaler, w)
    out = {}
    for name, (m, n) in extras.items():
        g = rl.build_groups(m, n, layer, phase="final", avg_rounds=False)
        rids = sorted(g)
        s = _final_scores(train, rl._run_labels(cg, cr), rl.compute_scores(g, rids, scaler, w))
        for i, r in enumerate(rids):
            out[(name, r)] = {meth: float(s[meth][i]) for meth in METHODS}
    return out


def global_run_scores(core: tuple, extras: dict, layers: list[int], log=print) -> dict:
    """Their Transfer protocol per run: probe on all of Core, scores averaged over layers/seeds."""
    jobs = [(core, extras, la, se) for la in layers for se in SEEDS]
    out = _average(_parallel(_global_job, jobs))
    log(f"  {len(jobs)} layer x seed runs done")
    return out
