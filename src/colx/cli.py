"""The `col` command-line interface.

Analysis commands are added as they are implemented, one subcommand per
experiment or pipeline stage.
"""

import platform
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from colx import __version__

app = typer.Typer(no_args_is_help=True, add_completion=False)
console = Console()

DATA_DIR = Path("data")
RESULTS_DIR = Path("results")


@app.command()
def info() -> None:
    """Show environment, data and results status."""
    table = Table(title=f"colx v{__version__}")
    table.add_column("Key")
    table.add_column("Value")
    table.add_row("python", platform.python_version())
    table.add_row("platform", platform.platform())
    table.add_row("data/", "present" if DATA_DIR.exists() else "missing (run: col fetch)")
    table.add_row("results/", "present" if RESULTS_DIR.exists() else "empty")
    console.print(table)


@app.command()
def fetch() -> None:
    """Download datasets and model assets (stub)."""
    console.print("[yellow]Not implemented yet.[/]")
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
