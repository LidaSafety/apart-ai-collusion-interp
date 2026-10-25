"""`col lens-judge private …`: the private-channel turn on Core (plan: stego.md, block D)."""

import json
from pathlib import Path
from typing import Annotated

import pandas as pd
import typer
from rich.console import Console

from colx.private.analyse import analyse
from colx.private.judge import run_private_judge
from colx.private.readout import write_private_tokens
from colx.provenance import LENS_PATH
from colx.turns.write import load_inputs

app = typer.Typer(no_args_is_help=True, help="Private-channel turn (exploratory).")
console = Console()

OUT_DIR = Path("results/private")
OutDir = Annotated[Path, typer.Option(help="Output folder.")]


@app.command()
def tokens(
    extract_dir: Annotated[Path, typer.Option(help="Stored Core extraction.")] = Path(
        "/workspace/extract/ours-qwen3_32b/qwen3_32b/core"
    ),
    model_dir: Annotated[Path, typer.Option(help="Qwen3-32B tokenizer + unembedding.")] = Path(
        "/root/qwen-unembed"
    ),
    lens: Annotated[Path, typer.Option(help="Qwen3-32B J-lens.")] = LENS_PATH,
    out_dir: OutDir = OUT_DIR,
) -> None:
    """Lens tokens of every colluder's private call (CPU)."""
    console.print(write_private_tokens(extract_dir, model_dir, lens, out_dir, console.print))


@app.command("analyse")
def analyse_cmd(
    out_dir: OutDir = OUT_DIR,
    round4_dir: Annotated[Path, typer.Option(help="Round-4 labels.")] = Path(
        "results/round4-judge"
    ),
    core_dir: Annotated[Path, typer.Option(help="Core transcripts.")] = Path(
        "third_party/narcbench/data/raw/qwen3_32b/core"
    ),
    n_boot: Annotated[int, typer.Option(help="Scenario-bootstrap draws.")] = 10_000,
    n_perm: Annotated[int, typer.Option(help="Label shuffles.")] = 10_000,
) -> None:
    """Held-out follow-through classifiers at the private turn, vs style (and text judge)."""
    recs = pd.DataFrame(analyse(out_dir, round4_dir, core_dir, n_boot, n_perm))
    console.print(
        recs[["instrument", "position", "test", "auroc", "p", "diff", "lower_95"]]
        .round(3)
        .to_string(index=False)
    )


@app.command()
def judge(
    model: Annotated[str, typer.Option(help="Judge model folder.")],
    judge_family: Annotated[str, typer.Option("--judge", help="qwen or gemma.")] = "qwen",
    out_dir: OutDir = OUT_DIR,
    round4_dir: Annotated[Path, typer.Option(help="Round-4 labels.")] = Path(
        "results/round4-judge"
    ),
    core_dir: Annotated[Path, typer.Option(help="Core transcripts.")] = Path(
        "third_party/narcbench/data/raw/qwen3_32b/core"
    ),
) -> None:
    """Frozen text judge on the private messages each colluder had seen (GPU)."""
    _, colluders, runs, _, _ = load_inputs(Path("results/discussion-turns"), round4_dir, core_dir)
    private = {
        r: json.loads((core_dir / r / "results.json").read_text())["private_messages"]
        for r in runs.run_id
    }
    console.print(
        run_private_judge(model, colluders, runs, private, out_dir, judge_family, console.print)
    )
