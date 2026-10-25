"""`col lens-judge transfer …`: the overlap detector on NARCBench-Transfer (plan: stego.md, C)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from colx.provenance import LENS_PATH
from colx.transfer.overlap import analyse

app = typer.Typer(no_args_is_help=True, help="Transfer tier (exploratory).")
console = Console()


@app.command()
def overlap(
    extract_dir: Annotated[Path, typer.Option(help="Stored transfer extraction.")] = Path(
        "/workspace/extract/ours-qwen3_32b/qwen3_32b/transfer"
    ),
    model_dir: Annotated[Path, typer.Option(help="Qwen3-32B tokenizer + unembedding.")] = Path(
        "/root/qwen-unembed"
    ),
    lens: Annotated[Path, typer.Option(help="Qwen3-32B J-lens.")] = LENS_PATH,
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = Path("results/transfer"),
    n_boot: Annotated[int, typer.Option(help="Scenario-bootstrap draws.")] = 10_000,
    n_perm: Annotated[int, typer.Option(help="Label shuffles.")] = 10_000,
) -> None:
    """Overlap detector, collusion vs control, on the transfer tier (CPU)."""
    console.print(analyse(extract_dir, model_dir, lens, out_dir, n_boot, n_perm))
