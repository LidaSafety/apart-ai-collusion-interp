"""`col lens-judge stego …`: steganographic collusion (plan: docs/plans/stego.md)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from colx.gemma.model import MODEL_ID
from colx.stego.gate import gate as run_gate
from colx.stego.generate import generate as run_generate

app = typer.Typer(no_args_is_help=True, help="Stego tier: lens vs text monitors, decoding.")
console = Console()

STEGO_DIR = Path("/root/narcbench-gemma/stego")


@app.command()
def generate(
    vllm_env: Annotated[Path, typer.Option(help="uv environment with vLLM.")] = Path(
        "/root/vllm-env"
    ),
    model_dir: Annotated[Path, typer.Option(help="Local model snapshot.")] = Path(
        "/dev/shm/gemma-3-27b-it"
    ),
    model_id: Annotated[str, typer.Option(help="Model id the server answers to.")] = MODEL_ID,
    out_dir: Annotated[Path, typer.Option(help="Where the stego runs are written.")] = STEGO_DIR,
    server_log: Annotated[Path, typer.Option(help="vLLM server log.")] = Path(
        "results/logs/vllm-stego.log"
    ),
    n_shoes: Annotated[
        int, typer.Option(help="Shoes (each gives a collusion and a control run).")
    ] = 50,
    workers: Annotated[int, typer.Option(help="Parallel stego.py workers.")] = 10,
) -> None:
    """Generate NARCBench-Stego with the private-line leak fixed (vLLM + leak-fixed stego.py)."""
    codes = run_generate(
        vllm_env, model_dir, model_id, out_dir, server_log, n_shoes, workers, console.print
    )
    if any(codes):
        raise typer.Exit(code=1)


@app.command()
def gate(stego_dir: Annotated[Path, typer.Option(help="Stego run folders.")] = STEGO_DIR) -> None:
    """Gate S: no leaked private lines, and the big player's bets follow the count."""
    verdict = run_gate(stego_dir)
    console.print(verdict)
    if not verdict["no leak"]:
        raise typer.Exit(code=1)
