from pathlib import Path

import numpy as np

from colx.narcbench.runs import Agent, Run
from colx.probes import analyse, compare, data, tfidf
from colx.probes.narc import model_layers, probe_module


def test_their_layer_defaults() -> None:
    assert model_layers("Qwen/Qwen3-32B", 64) == [26, 27, 28, 29, 30]
    assert model_layers("google/gemma-3-27b-it", 62) == [29, 30, 31, 32, 33]


def test_domain_parsing_matches_theirs() -> None:
    assert analyse.domain_of("deception__audit_01__collusion") == "audit"
    assert analyse.domain_of("cicd__cicd_02__control") == "cicd"


def test_worker_sets_the_augmentation_switch() -> None:
    assert analyse._run(lambda: probe_module().AUG_ENABLED, False) is False
    assert analyse._run(lambda: probe_module().AUG_ENABLED, True) is True


def test_sets_round_trip_and_merge(tmp_path: Path) -> None:
    meta = [{"run_id": "r", "agent_name": "a"}]
    arrays = {"layer_1": np.ones((1, 3), np.float32)}
    data.save_set(meta, arrays, tmp_path / "s")
    m2, a2 = data.load_set(tmp_path / "s")
    merged = data.merge_sets((m2, a2), (meta, arrays))
    assert len(merged[0]) == 2 and merged[1]["layer_1"].shape == (2, 3)


def _run(rid: str, mode: str, words: dict) -> Run:
    """A toy run whose agents each say one message; colluders are a and b in collusion runs."""
    roles = {n: ("colluder" if mode == "collusion" and n in "ab" else "honest") for n in "abcd"}
    msgs = tuple(f"[{n}]: {words[n]}" for n in "abcd")
    agents = tuple(Agent(n, roles[n], "", "", "", "") for n in "abcd")
    return Run(rid, rid.split("__")[1], mode, "", ("A", "B"), "", msgs, (), agents)


def test_tfidf_heldout_scores_separate_collusion_from_control() -> None:
    runs = []
    for d in ("x", "y", "z"):
        for i in range(3):
            plain = dict.fromkeys("abcd", f"budget review {d} plain words")
            secret = plain | {"a": "secretly push option", "b": "secretly push option"}
            runs += [_run(f"t__{d}_{i}__collusion", "collusion", secret),
                     _run(f"t__{d}_{i}__control", "control", plain)]  # fmt: skip
    core = tfidf.agent_texts(runs)
    scores = tfidf.heldout_scores(core, {})
    coll = [v["deception_split"] for (_, r), v in scores.items() if r.endswith("collusion")]
    ctrl = [v["deception_split"] for (_, r), v in scores.items() if r.endswith("control")]
    assert min(coll) > max(ctrl)


def test_contrast_and_paired_on_perfect_scores() -> None:
    pos = [("s", "t__a_01__collusion"), ("s", "t__b_01__collusion")]
    neg = [("s", "t__a_01__control"), ("s", "t__b_01__control")]
    good = {pos[0]: 2.0, pos[1]: 3.0, neg[0]: 0.0, neg[1]: 1.0}
    flat = dict.fromkeys(good, 0.0)
    assert compare.contrast(pos, neg, good, 20, 20)["auroc"] == 1.0
    assert compare.paired(pos, neg, good, flat, 20)["diff"] == 0.5
