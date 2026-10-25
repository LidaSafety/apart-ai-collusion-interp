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
