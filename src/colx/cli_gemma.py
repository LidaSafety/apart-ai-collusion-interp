"""`col lens-judge gemma …`: the Gemma-3-27B replication (plan: docs/plans/gemma.md)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from colx.gemma.extract import extract as run_extract
from colx.gemma.generate import generate as run_generate

app = typer.Typer(no_args_is_help=True, help="Gemma-3-27B replication with a converged lens.")
console = Console()

MODEL_DIR = Path("/dev/shm/gemma-3-27b-it")
CORE_DIR = Path("third_party/narcbench/data/raw/gemma_3_27b/core")
OUT_DIR = Path("results/gemma")

ModelDir = Annotated[Path, typer.Option(help="Local Gemma-3-27B-IT snapshot.")]
CoreDir = Annotated[Path, typer.Option(help="Gemma NARCBench Core transcripts.")]


@app.command()
def generate(
    vllm_env: Annotated[Path, typer.Option(help="uv environment with vLLM.")] = Path(
        "/root/vllm-env"
    ),
    model_dir: ModelDir = MODEL_DIR,
    core_dir: CoreDir = CORE_DIR,
    server_log: Annotated[Path, typer.Option(help="Where the vLLM server writes its log.")] = Path(
        "results/logs/vllm-server.log"
    ),
    test: Annotated[bool, typer.Option(help="3 scenarios only (smoke test).")] = False,
    parallel: Annotated[int, typer.Option(help="Scenarios run in parallel.")] = 8,
    eager: Annotated[
        bool, typer.Option(help="vLLM --enforce-eager (no compile, no CUDA graphs).")
    ] = False,
) -> None:
    """Generate NARCBench Core with Gemma: vLLM server plus NARCBench's unchanged core.py."""
    code = run_generate(
        vllm_env, model_dir, core_dir, server_log, test, parallel, eager, console.print
    )
    console.print(f"core.py exited with code {code}")
    raise typer.Exit(code=code)


@app.command()
def extract(
    model_dir: ModelDir = MODEL_DIR,
    core_dir: CoreDir = CORE_DIR,
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = OUT_DIR,
) -> None:
    """Residuals of every call at its read points, through Gemma (GPU)."""
    console.print(run_extract(core_dir, model_dir, out_dir, console.print))
