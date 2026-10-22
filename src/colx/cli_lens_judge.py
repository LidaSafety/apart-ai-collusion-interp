"""`col lens-judge …`: the round-4 lens-judge experiment (docs/plans/round4-judge.md)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from colx.narcbench.write import write_label_tables

app = typer.Typer(no_args_is_help=True, help="Round-4 lens-judge experiment.")
console = Console()

CORE_DIR = Path("third_party/narcbench/data/raw/qwen3_32b/core")
OUT_DIR = Path("results/round4-judge")

CoreDir = Annotated[Path, typer.Option(help="NARCBench Core transcripts (100 run folders).")]
OutDir = Annotated[Path, typer.Option(help="Output folder of the round-4 experiment.")]


def _print_counts(title: str, counts: dict[str, object]) -> None:
    """Print a two-column table of named counts."""
    table = Table(title=title)
    table.add_column("Count")
    table.add_column("Value", justify="right")
    for key, value in counts.items():
        table.add_row(key, str(value))
    console.print(table)


@app.command()
def labels(core_dir: CoreDir = CORE_DIR, out_dir: OutDir = OUT_DIR) -> None:
    """Derive run labels, style features and vote lines from the transcripts."""
    counts = write_label_tables(core_dir, out_dir)
    _print_counts("Round-4 labels", counts)
    console.print(f"Wrote {out_dir / 'agents.parquet'} and {out_dir / 'runs.parquet'}")
