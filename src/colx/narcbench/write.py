"""Write the round-4 label tables (`agents.parquet`, `runs.parquet`) with provenance."""

from pathlib import Path

from colx import provenance
from colx.narcbench.labels import agent_table, run_table
from colx.narcbench.runs import load_runs, system_prompts_constant
from colx.narcbench.summary import label_summary


def write_label_tables(core_dir: Path, out_dir: Path) -> dict[str, int]:
    """Build the agent and run tables from the transcripts, save them, return the counts."""
    runs = load_runs(core_dir)
    agents = agent_table(runs)
    run_rows = run_table(runs, agents)
    summary = label_summary(agents, run_rows)
    summary["runs_with_constant_system_prompts"] = sum(
        system_prompts_constant(core_dir / run.run_id) for run in runs
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = provenance.collect("col lens-judge labels", transcripts=str(core_dir), counts=summary)
    for name, table in (("agents", agents), ("runs", run_rows)):
        path = out_dir / f"{name}.parquet"
        table.to_parquet(path, index=False)
        provenance.write_meta(path, meta)
    return summary
