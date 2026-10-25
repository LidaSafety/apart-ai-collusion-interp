"""`col lens-judge probes …`: NARCBench's deception probes, reproduced (amendment 4)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

app = typer.Typer(no_args_is_help=True, help="NARCBench deception probes and TF-IDF baseline.")
console = Console()

OUT = Path("results/probes")
QWEN_EXTRACT = Path("/workspace/extract/ours-qwen3_32b/qwen3_32b")
GEMMA_CORE = Path("third_party/narcbench/data/raw/gemma_3_27b/core")
QWEN_CORE = Path("third_party/narcbench/data/raw/qwen3_32b/core")
QWEN_TRANSFER = Path("third_party/narcbench/data/raw/qwen3_32b/transfer")
STRESS_DIR = Path("/workspace/lens-judge/overlap-monitor/transcripts")
STRESS = ("aware", "para", "independent", "benign", "evade", "benign_budget", "benign_deadline",
          "benign_open")  # fmt: skip


@app.command("extract-qwen")
def extract_qwen(
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = OUT / "qwen",
) -> None:
    """Qwen3-32B Core and Transfer in NARCBench's format from stored `chat_end` (CPU)."""
    from colx.probes.data import save_set, stored_set
    from colx.probes.narc import model_layers

    layers = model_layers("Qwen/Qwen3-32B", 64)
    for name, phases in (("core", ("discussion", "final")), ("transfer", ("final",))):
        meta, arrays = stored_set(QWEN_EXTRACT / name, layers, phases)
        save_set(meta, arrays, out_dir / name)
        console.print(f"{name}: {len(meta)} calls, layers {layers}")


@app.command("extract-gemma")
def extract_gemma(
    model_dir: Annotated[Path, typer.Option(help="Local Gemma-3-27B-IT snapshot.")] = Path(
        "/dev/shm/gemma-3-27b-it"
    ),
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = OUT / "gemma",
    dry_run: Annotated[bool, typer.Option(help="First 3 calls of Core only.")] = False,
    only: Annotated[
        list[str] | None, typer.Option("--set", help="Extract only these sets (repeat).")
    ] = None,
) -> None:
    """Gemma Core and the stress sets with NARCBench's extraction recipe (GPU)."""
    from colx.probes.extract import extract_gemma as run
    from colx.probes.extract import extract_samples, select_samples
    from colx.probes.narc import model_layers

    layers = model_layers("google/gemma-3-27b-it", 62)
    sets = {"core": (GEMMA_CORE, ("discussion", "final"), ("collusion", "control"))}
    sets |= {c: (STRESS_DIR / c, ("final",), ("collusion",)) for c in STRESS}
    if only:
        sets = {k: v for k, v in sets.items() if k in only}
    if dry_run:
        from colx.backends import BACKENDS

        tokenizer, model = BACKENDS["gemma"].load(model_dir)
        samples = select_samples(GEMMA_CORE, ("discussion",), ("collusion",))[:3]
        meta, arrays = extract_samples(model, tokenizer, samples, layers, console.print)
        console.print(meta[0], {k: v.shape for k, v in arrays.items()})
        return
    console.print(run(model_dir, sets, layers, out_dir, console.print))


@app.command()
def reproduce(
    model: Annotated[str, typer.Option(help="qwen or gemma.")] = "qwen",
    augment: Annotated[
        bool, typer.Option(help="Their released code's noise augmentation (paper text: off).")
    ] = True,
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = OUT,
) -> None:
    """Their protocol and aggregation: Core leave-domain-out and Transfer (CPU)."""
    import json

    from colx import provenance
    from colx.probes.analyse import paper_metrics
    from colx.probes.data import load_set
    from colx.probes.narc import model_layers, probe_module

    probe_module().AUG_ENABLED = augment
    layers = model_layers("Qwen/Qwen3-32B" if model == "qwen" else "google/gemma-3-27b-it",
                          64 if model == "qwen" else 62)  # fmt: skip
    core = load_set(out_dir / model / "core")
    transfer = load_set(out_dir / model / "transfer") if model == "qwen" else None
    result = paper_metrics(core, layers, transfer, console.print)
    meta = provenance.collect("col lens-judge probes reproduce", label="planned (amendment 4)",
                              model=model, augment=augment, layers=layers)  # fmt: skip
    name = f"paper_metrics{'' if augment else '_noaug'}.json"
    (out_dir / model / name).write_text(json.dumps(meta | result, indent=1))
    console.print(result)


def _overlap_scores() -> dict:
    """Lens-raw overlap score per (set, run_id), on the same keys the probe uses."""
    import pandas as pd

    from colx.narcbench.runs import load_runs
    from colx.overlap import extras as ex
    from colx.overlap.compare import run_frame

    out = {}
    for name, path in (("gemma", "gemma"), ("qwen", "qwen"), ("transfer", "transfer")):
        t = pd.read_parquet(f"results/overlap/text/{path}.parquet")
        t = t[t.instrument == "lens_raw"]
        out |= {(name, r): float(s) for r, s in zip(t.run_id, t.run_score, strict=True)}
    for c in STRESS:
        frame = run_frame([r for r in load_runs(STRESS_DIR / c) if r.mode == "collusion"])
        tok = pd.read_parquet(Path("results/overlap") / c / "final_tokens.parquet")
        sets = ex.entry_sets(tok[(tok.rendering == "raw") & (tok.position == "P1")])
        out |= dict(zip([(c, r) for r in frame.run_id], ex.run_scores(frame, sets), strict=True))
    return out


@app.command()
def compare(
    out_dir: Annotated[Path, typer.Option(help="Output folder.")] = OUT,
    n_boot: Annotated[int, typer.Option(help="Scenario-bootstrap draws.")] = 10_000,
    n_perm: Annotated[int, typer.Option(help="Label shuffles.")] = 10_000,
) -> None:
    """Amendment 4: probe vs overlap vs TF-IDF on identical runs (K1-K3 and secondary)."""
    import json

    from colx import provenance
    from colx.narcbench.runs import load_runs
    from colx.overlap.compare import _transfer_runs
    from colx.probes import analyse, tfidf
    from colx.probes import compare as cmp
    from colx.probes.data import load_set
    from colx.probes.narc import model_layers

    g_layers = model_layers("google/gemma-3-27b-it", 62)
    q_layers = model_layers("Qwen/Qwen3-32B", 64)
    gcore = load_set(out_dir / "gemma" / "core")
    gx = {c: load_set(out_dir / "gemma" / c) for c in STRESS}
    qcore, qtr = load_set(out_dir / "qwen" / "core"), load_set(out_dir / "qwen" / "transfer")
    console.print("probe: Gemma held-out, final calls")
    pf = analyse.heldout_run_scores(gcore, gx, g_layers, "final", console.print)
    console.print("probe: Gemma and Qwen Core held-out, their Core protocol; Qwen Transfer")
    pg = analyse.heldout_run_scores(gcore, {}, g_layers, "discussion", console.print)
    pq = analyse.heldout_run_scores(qcore, {}, q_layers, "discussion", console.print)
    pt = analyse.global_run_scores(qcore, {"transfer": qtr}, q_layers, console.print)
    texts = {"gemma": tfidf.agent_texts(load_runs(GEMMA_CORE)),
             "qwen": tfidf.agent_texts(load_runs(QWEN_CORE))}  # fmt: skip
    tx = {c: tfidf.agent_texts([r for r in load_runs(STRESS_DIR / c) if r.mode == "collusion"])
          for c in STRESS}  # fmt: skip
    ttr = tfidf.agent_texts(
        _transfer_runs(Path("third_party/narcbench/data/raw/qwen3_32b/transfer"))
    )
    tf = {"gemma": tfidf.heldout_scores(texts["gemma"], tx),
          "qwen": tfidf.heldout_scores(texts["qwen"], {}),
          "transfer": tfidf.global_scores(texts["qwen"], {"transfer": ttr}),
          "null_gemma": tfidf.heldout_scores(texts["gemma"], {}, shuffle_seed=0),
          "null_qwen": tfidf.heldout_scores(texts["qwen"], {}, shuffle_seed=0)}  # fmt: skip
    ov = _overlap_scores()
    record = cmp.analyse(pf, pg, pq, pt, tf, ov, n_boot, n_perm)
    meta = provenance.collect("col lens-judge probes compare", label="planned (amendment 4)")
    (out_dir / "compare.json").write_text(json.dumps(meta | record, indent=1, default=str))
    console.print(record["primary"], record["summary"])
