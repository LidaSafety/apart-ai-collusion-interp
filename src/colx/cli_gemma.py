"""`col lens-judge gemma …`: the Gemma-3-27B replication (plan: docs/plans/gemma.md)."""

from pathlib import Path
from typing import Annotated

import pandas as pd
import typer
from rich.console import Console

from colx.gemma.analyse import analyse as run_analyse
from colx.gemma.extract import extract as run_extract
from colx.gemma.gate import api_errors, gate
from colx.gemma.generate import generate as run_generate
from colx.gemma.readout import write_readouts
from colx.gemma.reference import write_check
from colx.narcbench.write import write_label_tables

app = typer.Typer(no_args_is_help=True, help="Gemma-3-27B replication with a converged lens.")
console = Console()

MODEL_DIR = Path("/dev/shm/gemma-3-27b-it")
CORE_DIR = Path("third_party/narcbench/data/raw/gemma_3_27b/core")
OUT_DIR = Path("results/gemma")
LENS_PATH = Path(
    "/workspace/lenses/neuronpedia-gemma-3-27b-it/gemma-3-27b-it/jlens/Salesforce-wikitext/"
    "gemma-3-27b-it_jacobian_lens.pt"
)

ModelDir = Annotated[Path, typer.Option(help="Local Gemma-3-27B-IT snapshot.")]
CoreDir = Annotated[Path, typer.Option(help="Gemma NARCBench Core transcripts.")]


@app.command()
def generate(
    vllm_env: Annotated[Path, typer.Option(help="uv environment with vLLM.")] = Path(
        "/root/vllm-env"
    ),
    model_dir: ModelDir = MODEL_DIR,
    core_dir: CoreDir = CORE_DIR,
    server_log: Annotated[Path, typer.Option(help="Where the vLLM server writes its log.")] = Path(
        "results/logs/vllm-server.log"
    ),
    test: Annotated[bool, typer.Option(help="3 scenarios only (smoke test).")] = False,
    parallel: Annotated[int, typer.Option(help="Scenarios run in parallel.")] = 8,
    eager: Annotated[
        bool, typer.Option(help="vLLM --enforce-eager (no compile, no CUDA graphs).")
    ] = False,
) -> None:
    """Generate NARCBench Core with Gemma: vLLM server plus NARCBench's unchanged core.py."""
    code = run_generate(
        vllm_env, model_dir, core_dir, server_log, test, parallel, eager, console.print
    )
    console.print(f"core.py exited with code {code}")
    raise typer.Exit(code=code)


@app.command()
def extract(
    model_dir: ModelDir = MODEL_DIR,
    core_dir: CoreDir = CORE_DIR,
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = OUT_DIR,
) -> None:
    """Residuals of every call at its read points, through Gemma (GPU)."""
    console.print(run_extract(core_dir, model_dir, out_dir, console.print))


@app.command()
def labels(
    core_dir: CoreDir = CORE_DIR,
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = OUT_DIR,
) -> None:
    """Label tables from the Gemma transcripts, then Gate 1 (exit 1 if it fails)."""
    write_label_tables(core_dir, out_dir)
    agents = pd.read_parquet(out_dir / "agents.parquet")
    runs = pd.read_parquet(out_dir / "runs.parquet")
    verdict = gate(agents, runs, api_errors(core_dir))
    console.print(verdict)
    if not verdict["passes"]:
        raise typer.Exit(code=1)


@app.command()
def tokens(
    model_dir: ModelDir = MODEL_DIR,
    lens: Annotated[Path, typer.Option(help="Gemma J-lens file.")] = LENS_PATH,
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = OUT_DIR,
) -> None:
    """Raw and words-relative top-25 lens tokens at P1, P2 and every discussion turn (GPU)."""
    console.print(write_readouts(model_dir, lens, out_dir, console.print))


@app.command()
def analyse(
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = OUT_DIR,
    n_boot: Annotated[int, typer.Option(help="Scenario-bootstrap draws.")] = 10_000,
    n_perm: Annotated[int, typer.Option(help="Label shuffles.")] = 10_000,
) -> None:
    """Overlap tests, the instruction classifier, and the Holm-corrected primary family."""
    console.print(
        pd.DataFrame(run_analyse(out_dir, n_boot, n_perm)).round(3).to_string(index=False)
    )


@app.command("check-lens")
def check_lens(
    model_dir: ModelDir = MODEL_DIR,
    lens: Annotated[Path, typer.Option(help="Gemma J-lens file.")] = LENS_PATH,
    core_dir: CoreDir = CORE_DIR,
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = OUT_DIR,
) -> None:
    """Our Gemma readout vs the pinned jacobian-lens library at layer 41 (GPU)."""
    result = write_check(model_dir, lens, core_dir, out_dir)
    console.print({k: v for k, v in result.items() if k != "reference_top25"})
    if not result["passes"]:
        raise typer.Exit(code=1)
