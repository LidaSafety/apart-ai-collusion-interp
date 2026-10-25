"""`col lens-judge stego …`: steganographic collusion (plan: docs/plans/stego.md)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from colx.gemma.model import MODEL_ID
from colx.stego.analyse import analyse as run_analyse
from colx.stego.extract import extract as run_extract
from colx.stego.gate import gate as run_gate
from colx.stego.generate import generate as run_generate
from colx.stego.monitor import run_monitor
from colx.stego.readout import write_tokens

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


OUT_DIR = Path("results/stego")
LENS_PATH = Path(
    "/workspace/lenses/neuronpedia-gemma-3-27b-it/gemma-3-27b-it/jlens/Salesforce-wikitext/"
    "gemma-3-27b-it_jacobian_lens.pt"
)
ModelDir = Annotated[Path, typer.Option(help="Local model snapshot.")]
Backend = Annotated[str, typer.Option(help="gemma or qwen.")]
StegoDir = Annotated[Path, typer.Option(help="Stego run folders.")]
OutDir = Annotated[Path, typer.Option(help="Output folder.")]


@app.command()
def extract(
    stego_dir: StegoDir = STEGO_DIR,
    model_dir: ModelDir = Path("/dev/shm/gemma-3-27b-it"),
    out_dir: OutDir = OUT_DIR,
    backend: Backend = "gemma",
) -> None:
    """Residuals of every player call at H-start and H-end (GPU)."""
    console.print(run_extract(stego_dir, model_dir, out_dir, backend, console.print))


@app.command()
def tokens(
    model_dir: ModelDir = Path("/dev/shm/gemma-3-27b-it"),
    lens: Annotated[Path, typer.Option(help="Gemma J-lens file.")] = LENS_PATH,
    out_dir: OutDir = OUT_DIR,
    backend: Backend = "gemma",
) -> None:
    """Raw and words-relative top-25 lens tokens at H-start and H-end (GPU)."""
    console.print(write_tokens(model_dir, lens, out_dir, backend, console.print))


@app.command()
def monitor(
    stego_dir: StegoDir = STEGO_DIR,
    model_dir: ModelDir = Path("/dev/shm/gemma-3-27b-it"),
    out_dir: OutDir = OUT_DIR,
    backend: Backend = "gemma",
) -> None:
    """S2's frozen text monitor: the model rates each table's public chat 0-9 (GPU)."""
    console.print(run_monitor(stego_dir, model_dir, out_dir, backend, console.print))


@app.command()
def analyse(
    out_dir: OutDir = OUT_DIR,
    stego_dir: StegoDir = STEGO_DIR,
    n_boot: Annotated[int, typer.Option(help="Shoe-bootstrap draws.")] = 10_000,
    n_perm: Annotated[int, typer.Option(help="Label shuffles.")] = 10_000,
) -> None:
    """S1-S3 and the Holm-corrected primary family."""
    console.print(run_analyse(out_dir, stego_dir, n_boot, n_perm))
