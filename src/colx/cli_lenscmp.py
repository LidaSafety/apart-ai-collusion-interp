"""`col lens-judge lenscmp`: J-lens vs J++ lens on Qwen3-4B (stego plan, block F)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from colx.lenscmp.analyse import compare_lenses

app = typer.Typer(no_args_is_help=True, help="J-lens vs J++ lens (block F, exploratory).")
console = Console()


@app.command()
def run(
    base_dir: Annotated[Path, typer.Option(help="Labels, calls, residuals.")] = Path(
        "results/qwen4b"
    ),
    core_dir: Annotated[Path, typer.Option(help="Qwen3-4B Core transcripts.")] = Path(
        "/root/narcbench-qwen4b/core"
    ),
    jlens_dir: Annotated[Path, typer.Option(help="J-lens token tables.")] = Path(
        "results/qwen4b-jlens"
    ),
    jpp_dir: Annotated[Path, typer.Option(help="J++ lens token tables.")] = Path(
        "results/qwen4b-jpp"
    ),
    n_boot: Annotated[int, typer.Option(help="Bootstrap draws.")] = 10_000,
    n_perm: Annotated[int, typer.Option(help="Label shuffles.")] = 10_000,
) -> None:
    """F1-F3 with each lens and the paired J++ - J differences."""
    console.print(
        compare_lenses(base_dir, core_dir, {"jlens": jlens_dir, "jpp": jpp_dir}, n_boot, n_perm)
    )
