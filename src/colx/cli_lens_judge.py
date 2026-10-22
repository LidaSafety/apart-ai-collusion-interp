"""`col lens-judge …`: the round-4 lens-judge experiment (docs/plans/round4-judge.md)."""

from pathlib import Path
from typing import Annotated

import pandas as pd
import typer
from rich.console import Console
from rich.table import Table

from colx.extract.check import DEFAULT_RUNS, blocks_below, write_check
from colx.extract.stored import write_stored
from colx.jlens.diagnostic import run_diagnostic
from colx.jlens.filtered import write_views
from colx.jlens.reference import write_reference_check
from colx.jlens.tokens import write_lens_tokens
from colx.narcbench.write import write_label_tables
from colx.provenance import LENS_PATH, MODEL_ID
from colx.qwen import local_dir

app = typer.Typer(no_args_is_help=True, help="Round-4 lens-judge experiment.")
console = Console()

CORE_DIR = Path("third_party/narcbench/data/raw/qwen3_32b/core")
OUT_DIR = Path("results/round4-judge")

CoreDir = Annotated[Path, typer.Option(help="NARCBench Core transcripts (100 run folders).")]
EXTRACT_DIR = Path("/workspace/extract/ours-qwen3_32b/qwen3_32b/core")
ExtractDir = Annotated[Path, typer.Option(help="Stored extraction (shards/ and samples.parquet).")]
ModelPath = Annotated[str, typer.Option(help="Qwen3-32B: Hub id or a local snapshot folder.")]
LensPath = Annotated[Path, typer.Option(help="J-lens file (neuronpedia Qwen3-32B lens.pt).")]
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


@app.command("check-lens")
def check_lens(
    model: ModelPath = MODEL_ID, lens: LensPath = LENS_PATH, out_dir: OutDir = OUT_DIR
) -> None:
    """Check our J-lens readout against the pinned reference library at layer 39 (GPU)."""
    result = write_reference_check(model, lens, out_dir)
    top = result.pop("reference_top25")
    _print_counts("J-lens reference check", result)
    console.print("Reference top-25 at layer 39:", top)
    if not (result["same_top25_tokens"] and result["logits_within_tolerance"]):
        raise typer.Exit(code=1)


@app.command("lens-tokens")
def lens_tokens(
    model: ModelPath = MODEL_ID,
    lens: LensPath = LENS_PATH,
    out_dir: OutDir = OUT_DIR,
    device: Annotated[str, typer.Option(help="cpu or cuda; the result is the same.")] = "cpu",
) -> None:
    """Top-25 J-lens tokens at the 10 layers, for every agent at P1 and P2."""
    summary = write_lens_tokens(local_dir(model), lens, out_dir, device)
    _print_counts("J-lens tokens", summary)
    overlap = pd.read_parquet(out_dir / "lens_overlap.parquet")
    console.print("Within-run overlap of the agents' top-25 lists (mean):")
    console.print(overlap.pivot(index="layer", columns="position", values="mean").round(3))
    console.print(f"Wrote {out_dir / 'lens_tokens.parquet'} and {out_dir / 'lens_grids.parquet'}")


@app.command()
def diagnose(
    model: ModelPath = MODEL_ID,
    lens: LensPath = LENS_PATH,
    extract_dir: ExtractDir = EXTRACT_DIR,
    out_dir: OutDir = OUT_DIR,
) -> None:
    """Exploratory lens diagnostic: library examples, system_end and relative P2 (GPU)."""
    verdicts = run_diagnostic(model, lens, extract_dir, out_dir)
    console.print_json(data=verdicts)


@app.command("lens-tokens-filtered")
def lens_tokens_filtered(
    model: ModelPath = MODEL_ID,
    lens: LensPath = LENS_PATH,
    out_dir: OutDir = OUT_DIR,
    device: Annotated[str, typer.Option(help="cpu or cuda; the result is the same.")] = "cpu",
) -> None:
    """Exploratory: top-25 words-only lens tokens, raw and with common content removed."""
    summary = write_views(local_dir(model), lens, out_dir, device)
    _print_counts("Filtered lens tokens (exploratory)", summary)
