"""`col lens-judge joint …`: the joint (Level-1) judge (docs/plans/joint-judge.md)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from colx.joint.run import run_joint, write_inputs
from colx.provenance import MODEL_ID

app = typer.Typer(no_args_is_help=True, help="Joint judge: all four agents in one prompt.")
console = Console()

ROUND4_DIR = Path("results/round4-judge")
OUT_DIR = Path("results/joint-judge")

Round4Dir = Annotated[Path, typer.Option(help="Round-4 outputs (labels, lens tokens, scores).")]
OutDir = Annotated[Path, typer.Option(help="Output folder of the joint judge.")]


def _print_counts(title: str, counts: dict[str, object]) -> None:
    """Print a two-column table of named counts."""
    table = Table(title=title)
    table.add_column("Count")
    table.add_column("Value", justify="right")
    for key, value in counts.items():
        table.add_row(key, str(value))
    console.print(table)


@app.command()
def prompts(
    round4_dir: Round4Dir = ROUND4_DIR,
    out_dir: OutDir = OUT_DIR,
    run: Annotated[str, typer.Option(help="Run whose prompts to print.")] = (
        "deception__audit_01__collusion"
    ),
) -> None:
    """Pool the lens tokens, build all 500 prompts, and print one run's prompt per arm."""
    table = write_inputs(round4_dir, out_dir, None)
    shown = table[(table.run_id == run) & (table.position != "P2")]
    for row in shown.itertuples():
        console.rule(f"{row.arm} {row.position} · {row.run_id}")
        console.print(row.prompt, markup=False, highlight=False)
    console.print(f"Wrote {len(table)} prompts to {out_dir / 'prompts.parquet'}")


@app.command()
def judge(
    model: Annotated[str, typer.Option(help="Qwen3-32B: Hub id or local folder.")] = MODEL_ID,
    round4_dir: Round4Dir = ROUND4_DIR,
    out_dir: OutDir = OUT_DIR,
    dry_run: Annotated[
        bool, typer.Option(help="2 runs, format checks only (no scores shown).")
    ] = False,
) -> None:
    """Score every joint prompt (0-9 rating) and generate the named pair (GPU)."""
    checks = run_joint(model, round4_dir, out_dir, dry_run, log=console.print)
    _print_counts("Answer-format checks", checks)
