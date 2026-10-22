"""Provenance written next to every lens-judge output.

The plan requires each output to record seeds, library versions, the model revision, the
pinned submodule commits, the lens's fitting-code commit and the lens sha256. This module
gathers them into one dict; commands write it as `<output>.meta.json`.
"""

import json
import platform
import subprocess
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

MODEL_ID = "Qwen/Qwen3-32B"
MODEL_REVISION = "9216db5781bf21249d130ec9da846c4624c16137"
LENS_PATH = Path("/workspace/lenses/neuronpedia-qwen3-32b/lens.pt")
LENS_SHA256 = "0af5ccf2e1c251bedc202607a7ca214f3b9f60980bab73d67a3d0b887db213d8"
LENS_FIT_COMMIT = "hijohnnylin/neuronpedia@22f0412f62c9d86860fb6c7c44aed1e2cd843256"
NARCBENCH_DIR = Path("third_party/narcbench")
JLENS_DIR = Path("third_party/jacobian-lens")
SEED = 0

_PACKAGES = ("numpy", "pandas", "scipy", "torch", "transformers", "safetensors", "colx")


def _git_head(repo: Path) -> str:
    """Return the commit checked out in `repo`, or "unknown" outside git."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return out.stdout.strip()


def _versions() -> dict[str, str]:
    """Return the installed version of each package that shapes the results."""
    found = {"python": platform.python_version()}
    for name in _PACKAGES:
        try:
            found[name] = version(name)
        except PackageNotFoundError:
            found[name] = "not installed"
    return found


def collect(command: str, *, seed: int = SEED, **extra: Any) -> dict[str, Any]:
    """Build the provenance record for one command run."""
    return {
        "command": command,
        "label": "planned",
        "time_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "seed": seed,
        "versions": _versions(),
        "repo_commit": _git_head(Path()),
        "narcbench_commit": _git_head(NARCBENCH_DIR),
        "jacobian_lens_commit": _git_head(JLENS_DIR),
        "model": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "lens_fit_commit": LENS_FIT_COMMIT,
        "lens_sha256": LENS_SHA256,
        **extra,
    }


def write_meta(output: Path, record: dict[str, Any]) -> Path:
    """Write `record` as `<output>.meta.json` and return that path."""
    path = output.with_name(output.name + ".meta.json")
    path.write_text(json.dumps(record, indent=2, default=str) + "\n")
    return path
