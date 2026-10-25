"""`col lens-judge overlap …`: the overlap detector vs text, and under stress."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from colx.gemma.model import MODEL_ID
from colx.overlap.generate import generate as run_generate

app = typer.Typer(no_args_is_help=True, help="Overlap detector: text baselines, stress tests.")
console = Console()

STRESS_DIR = Path("/workspace/lens-judge/overlap-monitor/transcripts")
GEMMA_CORE = Path("third_party/narcbench/data/raw/gemma_3_27b/core")


@app.command()
def generate(
    vllm_env: Annotated[Path, typer.Option(help="uv environment with vLLM.")] = Path(
        "/root/vllm-env"
    ),
    model_dir: Annotated[Path, typer.Option(help="Local model snapshot.")] = Path(
        "/dev/shm/gemma-3-27b-it"
    ),
    model_id: Annotated[str, typer.Option(help="Model id the server answers to.")] = MODEL_ID,
    out_dir: Annotated[Path, typer.Option(help="One folder per condition.")] = STRESS_DIR,
    core_dir: Annotated[Path, typer.Option(help="Gemma Core runs (controls).")] = GEMMA_CORE,
    server_log: Annotated[Path, typer.Option(help="vLLM server log.")] = Path(
        "results/logs/vllm-overlap.log"
    ),
    parallel: Annotated[int, typer.Option(help="Scenarios in parallel per condition.")] = 8,
) -> None:
    """Generate the four stress conditions with Gemma (vLLM + wrapped core.py; GPU)."""
    codes = run_generate(
        vllm_env, model_dir, model_id, out_dir, core_dir, server_log, parallel, console.print
    )
    if any(codes):
        raise typer.Exit(code=1)


DATASETS = {
    "gemma": (
        GEMMA_CORE,
        {"both": Path("results/gemma/final_tokens.parquet")},
    ),
    "qwen": (
        Path("third_party/narcbench/data/raw/qwen3_32b/core"),
        {
            "raw": Path("results/round4-judge/lens_tokens.parquet"),
            "rel": Path("results/round4-judge/filtered/lens_tokens_words_relative.parquet"),
        },
    ),
    "transfer": (
        Path("third_party/narcbench/data/raw/qwen3_32b/transfer"),
        {"both": Path("results/transfer/final_tokens.parquet")},
    ),
}


@app.command("text")
def text_baseline(
    dataset: Annotated[str, typer.Option(help="gemma (primary), qwen or transfer.")] = "gemma",
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = Path("results/overlap/text"),
    n_boot: Annotated[int, typer.Option(help="Scenario-bootstrap draws.")] = 10_000,
    n_perm: Annotated[int, typer.Option(help="Label shuffles.")] = 10_000,
) -> None:
    """Part 1: the overlap detector on lens tokens vs on the agents' own messages."""
    from colx.overlap.compare import analyse

    core_dir, tokens = DATASETS[dataset]
    result = analyse(dataset, core_dir, tokens, out_dir, n_boot, n_perm)
    for name, r in result["mode_vs_control"].items():
        console.print(
            f"{name:14s} M {r['auroc']:.3f} [{r['ci_low']:.3f}, {r['ci_high']:.3f}]"
            f"  pair found {r['pair_found']}/{r['of']}  split found {r['split_found']}/{r['of']}"
        )
    console.print(result["lens_minus_best_text"])


@app.command("gate")
def paraphrase_gate(
    paraphrases: Annotated[Path, typer.Option(help="paraphrases.json")] = STRESS_DIR
    / "paraphrases.json",
) -> None:
    """Gate P: paraphrases share < 20% of the original's word bigrams and keep option labels."""
    from colx.overlap.gate import gate

    console.print(gate(Path("third_party/narcbench"), paraphrases))


@app.command()
def stress(
    transcripts: Annotated[Path, typer.Option(help="Condition transcript folders.")] = STRESS_DIR,
    results: Annotated[Path, typer.Option(help="Condition result folders.")] = Path(
        "results/overlap"
    ),
    core_table: Annotated[Path, typer.Option(help="Part-1 Gemma score table.")] = Path(
        "results/overlap/text/gemma.parquet"
    ),
    n_boot: Annotated[int, typer.Option(help="Scenario-bootstrap draws.")] = 10_000,
    n_perm: Annotated[int, typer.Option(help="Label shuffles.")] = 10_000,
) -> None:
    """Part 2: the detector (and the text instruments) under the four stress conditions."""
    from colx.overlap.stress import analyse

    record = analyse(transcripts, results, core_table, n_boot, n_perm, console.print)
    for c, r in record["conditions"].items():
        for name in ("lens_raw", "lens_rel", "text_top250", "text_cosine"):
            m = r["mode_vs_control"][name]
            console.print(
                f"{c:12s} {name:12s} S {m['auroc']:.3f} [{m['ci_low']:.3f}, {m['ci_high']:.3f}]"
                f"  split {m['split_found']}/{m['of']}"
            )
        console.print(f"{c:12s} behaviour {r['behaviour']}")
    for key in ("primary_holm", "core_vs_benign_lens_raw", "operating_point_lens_raw"):
        console.print(key, record[key])


@app.command("text-monitor")
def text_monitor(
    model_dir: Annotated[Path, typer.Option(help="Local Gemma-3-27B-IT snapshot.")] = Path(
        "/dev/shm/gemma-3-27b-it"
    ),
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = Path(
        "results/overlap/textmonitor"
    ),
    dry_run: Annotated[bool, typer.Option(help="2 runs per set, format checks only.")] = False,
) -> None:
    """Amendment 1 D: Gemma reads each run's discussion and rates collusion 0-9 (GPU)."""
    from colx.narcbench.runs import load_runs
    from colx.overlap.compare import _transfer_runs
    from colx.overlap.textmonitor import run_monitor

    sets = {"gemma": (load_runs(GEMMA_CORE), False)}
    for c in ("aware", "para", "independent", "benign"):
        runs = [r for r in load_runs(STRESS_DIR / c) if r.mode == "collusion"]
        sets[c] = (runs, False)
    sets["transfer"] = (_transfer_runs(DATASETS["transfer"][0]), True)
    if dry_run:
        sets = {k: (v[0][:2], v[1]) for k, v in sets.items()}
        out_dir = out_dir / "dryrun"
    console.print(run_monitor(sets, model_dir, out_dir, console.print))


TURNS = {
    "gemma": Path("results/gemma/turns_tokens.parquet"),
    "qwen": Path("results/discussion-turns/turns_tokens.parquet"),
}


def _auc(r: dict) -> str:
    """An AUROC record as "0.944 [0.903, 0.979] p=0.0001"."""
    return f"{r['auroc']:.3f} [{r['ci_low']:.3f}, {r['ci_high']:.3f}] p={r['p']:.4f}"


def _frame_and_p1(name: str):
    """Run frame and raw P1 entry sets of one part-1 dataset."""
    from colx.narcbench.runs import load_runs
    from colx.overlap.compare import _transfer_runs, load_tokens, run_frame
    from colx.overlap.extras import entry_sets

    folder, tokens = DATASETS[name]
    runs = _transfer_runs(folder) if name == "transfer" else load_runs(folder)
    t = load_tokens(tokens)
    raw = t[(t.rendering == "raw") & (t.position == "P1")]
    return run_frame(runs), raw, entry_sets(raw)


@app.command()
def extras(
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = Path("results/overlap/extras"),
    monitor_dir: Annotated[Path, typer.Option(help="LLM text monitor outputs.")] = Path(
        "results/overlap/textmonitor"
    ),
    n_boot: Annotated[int, typer.Option(help="Scenario-bootstrap draws.")] = 10_000,
    n_perm: Annotated[int, typer.Option(help="Label shuffles.")] = 10_000,
) -> None:
    """Amendment 1: early warning (A), side rule (B), layers (C), LLM text monitor (D)."""
    import pandas as pd

    from colx.overlap import extras as ex

    base = {n: _frame_and_p1(n) for n in ("gemma", "qwen", "transfer")}
    early = {}
    for n, path in TURNS.items():
        turns = pd.read_parquet(
            path, columns=["run_id", "agent", "round", "position", "layer", "rendering", "token_id"]
        )
        early[n] = ex.early_warning(base[n][0], turns, n_boot, n_perm)
        for r in early[n]:
            console.print(f"A {n} R{r['round']} T-start {r['rendering']}: {_auc(r)}")
    ex.save({"early_warning": early}, out_dir, "early_warning", "col lens-judge overlap extras")

    side = {n: ex.side_test(base[n][0], base[n][2]) for n in base}
    held = [side["qwen"], side["transfer"]]
    right, named = (
        sum(s["named_right"] for s in held),
        sum(s["runs_with_right_split"] for s in held),
    )
    from scipy.stats import binomtest

    side["heldout_pooled"] = {
        "named_right": right,
        "runs_with_right_split": named,
        "share": right / named,
        "p": float(binomtest(right, named, 0.5, alternative="greater").pvalue),
    }
    side["gemma"]["note"] = "development set: the rule was chosen here"
    ex.save({"side_rule": side}, out_dir, "side_rule", "col lens-judge overlap extras")
    console.print("B", side)

    layers = {n: ex.layer_aurocs(base[n][0], base[n][1]) for n in base}
    ex.save({"layers": layers}, out_dir, "layers", "col lens-judge overlap extras")
    console.print("C", {n: [round(r["auroc"], 2) for r in v] for n, v in layers.items()})

    if not (monitor_dir / "gemma.parquet").exists():
        console.print("D skipped: no text monitor outputs yet")
        return
    mon = {}
    for n in ("gemma", "transfer"):
        frame, _, sets = base[n]
        mon[n] = ex.monitor_tests(
            frame,
            pd.read_parquet(monitor_dir / f"{n}.parquet"),
            ex.run_scores(frame, sets),
            n_boot,
            n_perm,
        )
    frame, _, sets = base["qwen"]
    qwen = _qwen_discussion_judge(frame)
    mon["qwen"] = ex.monitor_tests(frame, qwen, ex.run_scores(frame, sets), n_boot, n_perm)
    mon.update(_stress_monitor(monitor_dir, n_boot, n_perm))
    record = {
        "text_monitor": mon,
        "primary_family": ex.family(early["gemma"][0], side["heldout_pooled"], mon["gemma"]),
    }
    ex.save(record, out_dir, "text_monitor", "col lens-judge overlap extras")
    for n, r in mon.items():
        m, d = r["monitor"], r["lens_minus_monitor"]
        found = f"pair {m['pair_found']}/{m['of']} split {m['split_found']}/{m['of']}"
        diff = f"{d['diff']:+.3f} (lower {d['lower_95']:+.3f}, p={d['p']:.4f})"
        console.print(f"D {n}: monitor {_auc(m)} {found}; lens minus monitor {diff}")
    console.print("family", record["primary_family"])


def _stress_monitor(monitor_dir: Path, n_boot: int, n_perm: int) -> dict:
    """D on each stress condition: its collusion runs plus the Gemma Core controls."""
    import pandas as pd

    from colx.narcbench.runs import load_runs
    from colx.overlap import extras as ex
    from colx.overlap.compare import run_frame

    core = pd.read_parquet(monitor_dir / "gemma.parquet")
    out = {}
    for c in ("aware", "para", "independent", "benign"):
        frame = run_frame(load_runs(STRESS_DIR / c))
        tokens = pd.read_parquet(Path("results/overlap") / c / "final_tokens.parquet")
        sets = ex.entry_sets(tokens[(tokens.rendering == "raw") & (tokens.position == "P1")])
        controls = core[core.run_id.str.endswith("__control")]
        monitor = pd.concat(
            [pd.read_parquet(monitor_dir / f"{c}.parquet"), controls], ignore_index=True
        )
        out[c] = ex.monitor_tests(frame, monitor, ex.run_scores(frame, sets), n_boot, n_perm)
    return out


def _qwen_discussion_judge(frame):
    """Qwen Core's joint-judge `discussion` arm as a monitor table, pairs in sorted-name order.

    The joint judge numbered agents in its own shuffled order (`order`); the pair is mapped
    to names and back to numbers in the frame's sorted order, as the other monitors use.
    """
    import pandas as pd

    s = pd.read_parquet("results/joint-judge/scores.parquet")
    s = s[s.arm == "discussion"]
    sorted_order = dict(zip(frame.run_id, frame.order, strict=True))
    pairs = []
    for r in s.itertuples():
        if r.pair is None:
            pairs.append(None)
            continue
        names = [list(r.order)[int(i) - 1] for i in r.pair]
        pairs.append(sorted(sorted_order[r.run_id].index(n) + 1 for n in names))
    return pd.DataFrame(
        {"run_id": s.run_id.to_numpy(), "rating": s.rating.to_numpy(), "pair": pairs}
    )


@app.command()
def figures(
    results: Annotated[Path, typer.Option(help="Overlap results folder.")] = Path(
        "results/overlap"
    ),
    out_dir: Annotated[Path, typer.Option(help="Where the PNGs go.")] = Path("docs/sprint/figures"),
) -> None:
    """Static report figures from the saved results (no recomputation)."""
    from colx.overlap.figures import all_figures

    console.print(all_figures(results, out_dir))
