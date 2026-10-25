"""Generate NARCBench-Stego through one vLLM server and several leak-fixed workers.

stego.py runs one shoe at a time, which leaves the server mostly idle; we split the shoes
over `workers` processes (each runs `leakfix.py` on its slice), so vLLM batches their
requests. The server setup is the Gemma Core one (`colx.gemma.generate`: V0 engine).
"""

import os
import subprocess
from pathlib import Path

from colx.gemma.generate import ENGINE_ENV, PORT, server_command, wait_ready

LEAKFIX = Path(__file__).with_name("leakfix.py")
NARCBENCH = Path("third_party/narcbench")


def shoe_slices(n_shoes: int, workers: int, first: int = 0) -> list[list[int]]:
    """Shoes first..first+n-1 dealt round-robin to the workers (empty slices dropped)."""
    shoes = range(first, first + n_shoes)
    return [list(shoes[w::workers]) for w in range(workers) if shoes[w::workers]]


def generate(
    vllm_env: Path,
    model_dir: Path,
    model_id: str,
    out_dir: Path,
    server_log: Path,
    n_shoes: int,
    workers: int,
    log=print,
    strip_history: bool = False,
    first_shoe: int = 0,
) -> list[int]:
    """Start the server, run the workers to completion, stop the server; return exit codes."""
    out_dir.mkdir(parents=True, exist_ok=True)
    url = f"http://127.0.0.1:{PORT}/v1"
    with server_log.open("w") as handle:
        server = subprocess.Popen(
            server_command(vllm_env, model_dir, False, served_name=model_id),
            stdout=handle,
            stderr=subprocess.STDOUT,
            env=os.environ | ENGINE_ENV,
        )
        try:
            wait_ready(server, PORT, log=log)
            procs = []
            for i, shoes in enumerate(shoe_slices(n_shoes, workers, first_shoe)):
                wlog = server_log.with_name(f"{server_log.stem}-worker{i}.log").open("w")
                cmd = [
                    str(vllm_env / "bin" / "python"),
                    str(LEAKFIX),
                    str(NARCBENCH.resolve()),
                    str(out_dir.resolve()),
                    model_id,
                    url,
                    *map(str, shoes),
                ]
                env = os.environ | ({"STEGO_STRIP_HISTORY": "1"} if strip_history else {})
                procs.append(subprocess.Popen(cmd, stdout=wlog, stderr=subprocess.STDOUT, env=env))
            codes = [p.wait() for p in procs]
            log(f"workers finished with codes {codes}")
            return codes
        finally:
            server.terminate()
            server.wait(timeout=120)
