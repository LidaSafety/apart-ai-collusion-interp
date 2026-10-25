"""`col lens-judge nla …`: NLA descriptions of Gemma activations (stego plan, block E)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from colx.nla.convert import convert as run_convert
from colx.nla.describe import describe_all
from colx.nla.verbalize import Verbalizer

app = typer.Typer(no_args_is_help=True, help="NLA descriptions (block E).")
console = Console()

NLA_DIR = Path("/dev/shm/nla-av")
NlaDir = Annotated[Path, typer.Option(help="bf16 NLA verbalizer folder.")]


@app.command()
def convert(
    out_dir: NlaDir = NLA_DIR,
    tmp_dir: Annotated[Path, typer.Option(help="Scratch for one fp32 shard.")] = Path(
        "/root/nla-tmp"
    ),
) -> None:
    """Download kitft's Gemma-3-27B NLA verbalizer and store it in bf16."""
    console.print(f"{run_convert(out_dir, tmp_dir, console.print)} shards")


@app.command()
def sanity(
    model_dir: NlaDir = NLA_DIR,
    gemma_dir: Annotated[Path, typer.Option(help="Gemma Core outputs.")] = Path("results/gemma"),
) -> None:
    """Describe 5 Core P1 activations and print them (block E's sanity check)."""
    from colx.nla.describe import core_units

    units, vectors = core_units(gemma_dir)
    for unit, text in zip(
        units.head(5).itertuples(), Verbalizer(model_dir).describe(vectors[:5]), strict=True
    ):
        console.rule(f"{unit.run_id} · {unit.agent} ({unit.role})")
        console.print(text, markup=False)


@app.command()
def describe(
    model_dir: NlaDir = NLA_DIR,
    gemma_dir: Annotated[Path, typer.Option(help="Gemma Core outputs.")] = Path("results/gemma"),
    stego_dir: Annotated[Path, typer.Option(help="Gemma stego outputs.")] = Path("results/stego"),
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = Path("results/nla"),
) -> None:
    """NLA descriptions of the stego S3 units and the Core P1 activations (GPU)."""
    console.print(describe_all(model_dir, gemma_dir, stego_dir, out_dir, console.print))
