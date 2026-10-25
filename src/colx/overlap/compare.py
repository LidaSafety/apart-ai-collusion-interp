"""Lens overlap vs text overlap on one dataset (plan: overlap-monitor.md, part 1).

Every instrument gives one score and one top pair per run, with agents in sorted-name
order (numbers 1-4). Tests: collusion mode vs control (M), pair found in collusion runs,
and lens minus the best text instrument (D, paired scenario bootstrap).
"""

import json
from pathlib import Path

import pandas as pd

from colx import provenance
from colx.analysis.suite import auroc_test
from colx.joint.pairs import overlap_score
from colx.narcbench.runs import Agent, Run, load_runs
from colx.overlap import text
from colx.turns.analyse import versus

LENS = ("lens_raw", "lens_rel")


def run_frame(runs: list[Run]) -> pd.DataFrame:
    """One row per run: run_id, scenario_id, mode, agent order and the colluder pair."""
    rows = []
    for r in runs:
        order = sorted(a.name for a in r.agents)
        colluders = tuple(i + 1 for i, n in enumerate(order) if _role(r, n) == "colluder")
        rows.append(
            {
                "run_id": r.run_id,
                "scenario_id": r.scenario_id,
                "mode": r.mode,
                "order": order,
                "colluders": colluders or None,
            }
        )
    return pd.DataFrame(rows)


def _role(run: Run, name: str) -> str:
    """The role of one agent of a run."""
    return next(a.role for a in run.agents if a.name == name)


def text_scores(runs: list[Run], frame: pd.DataFrame) -> dict[str, list]:
    """Per text instrument, (score, pair) for every run, in frame order."""
    texts = [
        text.agent_text(list(r.public_messages), n, order)
        for r, order in zip(runs, frame.order, strict=True)
        for n in order
    ]
    tops, matrix = text.top_tfidf(texts)
    out = {k: [] for k in (*text.SET_INSTRUMENTS, "text_cosine")}
    for i in range(len(runs)):
        rows = range(4 * i, 4 * i + 4)
        sets = [text.word_sets(texts[j]) for j in rows]
        for k in ("text_words", "text_bigrams"):
            out[k].append(overlap_score([s[k] for s in sets]))
        out["text_top250"].append(overlap_score([tops[j] for j in rows]))
        out["text_cosine"].append(text.cosine_score(matrix[4 * i : 4 * i + 4]))
    return out


def lens_scores(tokens: pd.DataFrame, frame: pd.DataFrame, position: str = "P1") -> dict:
    """Per rendering, (score, pair) for every run from its P1 lens entries."""
    out = {}
    for rendering in ("raw", "rel"):
        sub = tokens[(tokens.rendering == rendering) & (tokens.position == position)]
        entries = {
            k: set(zip(g.layer, g.token_id, strict=True))
            for k, g in sub.groupby(["run_id", "agent"])
        }
        out[f"lens_{rendering}"] = [
            overlap_score([entries[(run_id, n)] for n in order])
            for run_id, order in zip(frame.run_id, frame.order, strict=True)
        ]
    return out


def score_table(scores: dict[str, list], frame: pd.DataFrame) -> pd.DataFrame:
    """Long table: run_id, instrument, run_score, pair_found and split_found (collusion runs).

    split_found (exploratory, added after seeing the data): the top pair is the colluders or
    the two honest agents, i.e. the score found the right 2-vs-2 split of the run.
    """
    rows = []
    for name, values in scores.items():
        for (score, pair), run_id, coll in zip(values, frame.run_id, frame.colluders, strict=True):
            found = None if coll is None else tuple(pair) == tuple(coll)
            split = None if coll is None else found or not set(pair) & set(coll)
            rows.append(
                {
                    "run_id": run_id,
                    "instrument": name,
                    "run_score": float(score),
                    "pair_found": found,
                    "split_found": split,
                }
            )
    return pd.DataFrame(rows)


def tests(table: pd.DataFrame, frame: pd.DataFrame, n_boot: int, n_perm: int) -> dict:
    """M and pair found per instrument; D (lens minus best text) per rendering."""
    wide = table.pivot(index="run_id", columns="instrument", values="run_score").loc[frame.run_id]
    y = (frame["mode"] == "collusion").to_numpy()
    scen = frame.scenario_id.to_numpy()
    m = {k: auroc_test(wide[k], y, scen, scen, n_boot, n_perm) for k in wide.columns}
    coll = table.dropna(subset=["pair_found"]).groupby("instrument")
    for k in m:
        m[k] |= {
            "pair_found": int(coll.pair_found.sum().get(k, 0)),
            "split_found": int(coll.split_found.sum().get(k, 0)),
            "of": int(coll.size().get(k, 0)),
        }
    texts = [k for k in wide.columns if k.startswith("text_")]
    best = max(texts, key=lambda k: m[k]["auroc"])
    d = {
        lens: {"best_text": best}
        | versus(wide[lens].to_numpy(), wide[best].to_numpy(), y, scen, n_boot)
        for lens in LENS
        if lens in wide.columns
    }
    return {"mode_vs_control": m, "lens_minus_best_text": d}


def load_tokens(paths: dict[str, Path]) -> pd.DataFrame:
    """Lens token tables, one per rendering or one with a `rendering` column, as one table."""
    frames = []
    for rendering, path in paths.items():
        t = pd.read_parquet(path, columns=None)
        if "rendering" not in t.columns:
            t = t.assign(rendering=rendering)
        frames.append(t[["run_id", "agent", "position", "layer", "token_id", "rendering"]])
    return pd.concat(frames, ignore_index=True).drop_duplicates()


def analyse(
    name: str, core_dir: Path, tokens: dict[str, Path], out_dir: Path, n_boot: int, n_perm: int
) -> dict:
    """Score every instrument on one dataset, test, and save `<name>.json` and `<name>.parquet`."""
    runs = load_runs(core_dir) if name != "transfer" else _transfer_runs(core_dir)
    frame = run_frame(runs)
    scores = text_scores(runs, frame) | lens_scores(load_tokens(tokens), frame)
    table = score_table(scores, frame)
    result = tests(table, frame, n_boot, n_perm)
    out_dir.mkdir(parents=True, exist_ok=True)
    table.merge(frame[["run_id", "scenario_id", "mode"]]).to_parquet(out_dir / f"{name}.parquet")
    meta = provenance.collect(
        f"col lens-judge overlap text ({name})",
        label="planned (overlap-monitor.md, part 1)",
        n_boot=n_boot,
        n_perm=n_perm,
        core_dir=str(core_dir),
        tokens={k: str(v) for k, v in tokens.items()},
    )
    (out_dir / f"{name}.json").write_text(json.dumps(meta | result, indent=1, default=str))
    return result


def load_transfer_run(run_dir: Path) -> Run:
    """A NARCBench-Transfer run as a Run with what the text instruments read.

    Transfer runs have no vote or option fields; only names, roles, mode, scenario and the
    public messages are filled (the other fields are empty).
    """
    config = json.loads((run_dir / "run_config.json").read_text())
    results = json.loads((run_dir / "results.json").read_text())
    agents = tuple(
        Agent(name=n, role=config["roles"][n], style="", system_prompt="", final_text="", vote="")
        for n in config["agents"]
    )
    return Run(
        run_id=config["run_id"],
        scenario_id=config["scenario_id"],
        mode=config["mode"],
        target_option="",
        option_labels=("", ""),
        final_user_prompt="",
        public_messages=tuple(results["public_messages"]),
        private_messages=tuple(results["private_messages"]),
        agents=agents,
    )


def _transfer_runs(transfer_dir: Path) -> list[Run]:
    """Every transfer run folder, sorted by run id."""
    dirs = sorted(d for d in transfer_dir.iterdir() if (d / "run_config.json").exists())
    return [load_transfer_run(d) for d in dirs]
