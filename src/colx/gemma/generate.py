"""Generate NARCBench Core with Gemma: a local vLLM server plus NARCBench's own core.py.

`third_party/narcbench/generation/core.py` runs unchanged (read-only), with its defaults
(temperature 0.7, max 512 tokens, its seeds for names and speaking order). It talks to an
OpenAI-style vLLM server, which we start from a separate environment (`--vllm-env`) and
stop afterwards. Sampling is not seeded per request, so replies are not exactly
reproducible (as for the Qwen data); the server's `--seed 0` is recorded.
The vLLM environment: vllm 0.10.1.1 with transformers 4.55.4 (transformers 5 configs break
this vLLM's Gemma 3 loader). The server runs vLLM's V0 engine: with the V1 engine, Gemma 3
produced gibberish on prompts longer than its 1,024-token sliding window (with either the
FlashAttention or Triton backend), while V0 and plain transformers answered sensibly
(probe logs of 2026-10-25, `results/logs/*vllm-probe*`).
"""

import os
import subprocess
import time
from pathlib import Path

import requests

from colx.gemma.model import MODEL_ID

CORE_PY = Path("third_party/narcbench/generation/core.py")
PORT = 8020
ENGINE_ENV = {"VLLM_USE_V1": "0"}


def server_command(vllm_env: Path, model_dir: Path, eager: bool, port: int = PORT) -> list[str]:
    """The vLLM serve command: the local snapshot, served under the Hub model id."""
    return [
        str(vllm_env / "bin" / "vllm"),
        "serve",
        str(model_dir),
        "--served-model-name",
        MODEL_ID,
        "--port",
        str(port),
        "--seed",
        "0",
        "--max-model-len",
        "8192",
        "--gpu-memory-utilization",
        "0.9",
        "--limit-mm-per-prompt",
        '{"image": 0}',
    ]


def wait_ready(server: subprocess.Popen, port: int, timeout_s: int = 1200, log=print) -> None:
    """Poll the server's model list until it answers; fail if it exits or times out."""
    start = time.time()
    while time.time() - start < timeout_s:
        if server.poll() is not None:
            raise RuntimeError(f"vLLM server exited with code {server.returncode}; see its log")
        try:
            if requests.get(f"http://127.0.0.1:{port}/v1/models", timeout=5).ok:
                log(f"vLLM ready after {time.time() - start:.0f}s")
                return
        except requests.ConnectionError:
            pass
        time.sleep(10)
    raise TimeoutError("vLLM server did not come up")


def generate(
    vllm_env: Path,
    model_dir: Path,
    out_dir: Path,
    server_log: Path,
    test: bool,
    parallel: int,
    eager: bool,
    log=print,
) -> int:
    """Start the server, run core.py into `out_dir`, stop the server; return core.py's code."""
    with server_log.open("w") as handle:
        server = subprocess.Popen(
            server_command(vllm_env, model_dir, eager),
            stdout=handle,
            stderr=subprocess.STDOUT,
            env=os.environ | ENGINE_ENV,
        )
        try:
            wait_ready(server, PORT, log=log)
            cmd = [
                str(vllm_env / "bin" / "python"),
                str(CORE_PY),
                "--model",
                MODEL_ID,
                "--output-dir",
                str(out_dir),
                "--base-url",
                f"http://127.0.0.1:{PORT}/v1",
                "--parallel",
                str(parallel),
                *(["--test"] if test else []),
            ]
            return subprocess.run(cmd, check=False).returncode
        finally:
            server.terminate()
            server.wait(timeout=120)
