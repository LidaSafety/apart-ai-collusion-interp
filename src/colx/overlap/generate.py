"""Generate the stress conditions through one vLLM server (plan: overlap-monitor.md, part 2).

Order: start the Gemma server (V0 engine, as for Core), write the paraphrases once, run the
four conditions' `variants.py` processes side by side (vLLM batches their requests), stop
the server. Then each condition folder gets the Core control runs as symlinks, so the
existing `col lens-judge gemma` labels/extract/tokens commands read one folder per condition.
"""

import os
import subprocess
from pathlib import Path

from colx.gemma.generate import ENGINE_ENV, PORT, server_command, wait_ready

VARIANTS = Path(__file__).with_name("variants.py")
NARCBENCH = Path("third_party/narcbench")
CONDITIONS = ("aware", "para", "independent", "benign")


def runner(vllm_env: Path, condition: str, target: Path, model_id: str, parallel: int) -> list:
    """The variants.py command for one condition (or `paraphrase`)."""
    return [
        str(vllm_env / "bin" / "python"),
        str(VARIANTS),
        str(NARCBENCH.resolve()),
        condition,
        str(target.resolve()),
        model_id,
        f"http://127.0.0.1:{PORT}/v1",
        str(parallel),
    ]


def link_controls(core_dir: Path, condition_dir: Path) -> int:
    """Symlink every Core control run into a condition folder; return how many."""
    n = 0
    for run in sorted(core_dir.glob("*__control")):
        link = condition_dir / run.name
        if not link.exists():
            link.symlink_to(run.resolve(), target_is_directory=True)
        n += 1
    return n


def _run_all(
    vllm_env: Path, out_dir: Path, model_id: str, parallel: int, log, conditions: tuple
) -> list[int]:
    """Paraphrases first (skipped if saved), then the given conditions at once."""
    para = out_dir / "paraphrases.json"
    if not para.exists():
        cmd = runner(vllm_env, "paraphrase", para, model_id, 0)
        if subprocess.run(cmd, check=False).returncode:
            raise RuntimeError("paraphrasing failed")
    log("paraphrases ready")
    procs = []
    for c in conditions:
        (out_dir / c).mkdir(parents=True, exist_ok=True)
        handle = (out_dir / f"generate-{c}.log").open("w")
        cmd = runner(vllm_env, c, out_dir / c, model_id, parallel)
        procs.append(subprocess.Popen(cmd, stdout=handle, stderr=subprocess.STDOUT))
    return [p.wait() for p in procs]


def generate(
    vllm_env: Path,
    model_dir: Path,
    model_id: str,
    out_dir: Path,
    core_dir: Path,
    server_log: Path,
    parallel: int,
    log=print,
    conditions: tuple = CONDITIONS,
) -> list[int]:
    """Start the server, generate the conditions, stop it, link controls; return exit codes."""
    out_dir.mkdir(parents=True, exist_ok=True)
    with server_log.open("w") as handle:
        server = subprocess.Popen(
            server_command(vllm_env, model_dir, False, served_name=model_id),
            stdout=handle,
            stderr=subprocess.STDOUT,
            env=os.environ | ENGINE_ENV,
        )
        try:
            wait_ready(server, PORT, log=log)
            codes = _run_all(vllm_env, out_dir, model_id, parallel, log, conditions)
        finally:
            server.terminate()
            server.wait(timeout=120)
    for c in conditions:
        log(f"{c}: linked {link_controls(core_dir, out_dir / c)} control runs")
    log(f"conditions finished with codes {codes}")
    return codes
