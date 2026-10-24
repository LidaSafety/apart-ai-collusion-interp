"""`col lens-judge turns …`: lens readouts of the discussion turns (plan: discussion-turns.md)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from colx.provenance import LENS_PATH
from colx.turns.run import write_tokens

app = typer.Typer(no_args_is_help=True, help="Discussion turns: does follow-through show early?")
console = Console()

EXTRACT_DIR = Path("/workspace/extract/ours-qwen3_32b/qwen3_32b/core")
OUT_DIR = Path("results/discussion-turns")

OutDir = Annotated[Path, typer.Option(help="Output folder of the discussion-turns experiment.")]


@app.command()
def tokens(
    model: Annotated[Path, typer.Option(help="Local Qwen3-32B folder (tokenizer, unembedding).")],
    lens: Annotated[Path, typer.Option(help="J-lens file.")] = LENS_PATH,
    extract_dir: Annotated[Path, typer.Option(help="Stored extraction.")] = EXTRACT_DIR,
    out_dir: OutDir = OUT_DIR,
    device: Annotated[str, typer.Option(help="cuda or cpu; the result is the same.")] = "cuda",
) -> None:
    """Read every stored discussion turn through the lens (raw and words-relative top 25)."""
    counts = write_tokens(extract_dir, model, lens, out_dir, device, log=console.print)
    console.print(counts)
