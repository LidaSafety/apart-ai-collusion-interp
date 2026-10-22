"""`col lens-judge …`: the round-4 lens-judge experiment (docs/plans/round4-judge.md)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from colx.extract.check import DEFAULT_RUNS, blocks_below, write_check
from colx.extract.stored import write_stored
from colx.narcbench.write import write_label_tables
from colx.provenance import MODEL_ID

app = typer.Typer(no_args_is_help=True, help="Round-4 lens-judge experiment.")
console = Console()

CORE_DIR = Path("third_party/narcbench/data/raw/qwen3_32b/core")
OUT_DIR = Path("results/round4-judge")

CoreDir = Annotated[Path, typer.Option(help="NARCBench Core transcripts (100 run folders).")]
EXTRACT_DIR = Path("/workspace/extract/ours-qwen3_32b/qwen3_32b/core")
ExtractDir = Annotated[Path, typer.Option(help="Stored extraction (shards/ and samples.parquet).")]
ModelPath = Annotated[str, typer.Option(help="Qwen3-32B: Hub id or a local snapshot folder.")]
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


@app.command()
def activations(extract_dir: ExtractDir = EXTRACT_DIR, out_dir: OutDir = OUT_DIR) -> None:
    """Load the stored round-4 residuals at P1 (prompt end) and P2 (end of discussion)."""
    summary = write_stored(extract_dir, out_dir)
    _print_counts("Stored round-4 activations", summary)
    console.print(f"Wrote {out_dir / 'activations.safetensors'} and its index table")


@app.command("check-activations")
def check_activations(
    model: ModelPath = MODEL_ID,
    out_dir: OutDir = OUT_DIR,
    runs: Annotated[list[str] | None, typer.Option(help="Runs to recompute.")] = None,
    with_response: Annotated[
        bool, typer.Option(help="Diagnostic: also run the reply tokens, as the extraction did.")
    ] = False,
) -> None:
    """Recompute 2 runs on the GPU and compare with the stored P1/P2 residuals."""
    table, verdicts = write_check(model, out_dir, tuple(runs or DEFAULT_RUNS), with_response)
    console.print(table.drop(columns=["run_id", "cos_p1", "cos_p2"]).T.to_string())
    _print_counts("Blocks with cosine below 0.999", blocks_below(table))
    _print_counts("Activation check verdicts", verdicts)
    if not all(verdicts.values()):
        raise typer.Exit(code=1)
