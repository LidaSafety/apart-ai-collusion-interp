"""Read-only access to NARCBench's own probe and extraction code (third_party, pinned).

Amendment 4 reproduces the deception probes of Rose et al. (arXiv 2604.01151) by calling
the released functions directly, so the recipe cannot drift from theirs:
`probes/reproduce_LR.py` (probe training, the five run statistics, their evaluation) and
`extraction/extract_core.py` (the chat rendering and the last-token hooks). Nothing under
third_party is modified; their module-level switches (e.g. augmentation) are set on the
imported module object only.
"""

import sys
from pathlib import Path

NARCBENCH = Path(__file__).resolve().parents[3] / "third_party" / "narcbench"


def _add_paths() -> None:
    """Make NARCBench's `config`, `colours` and script modules importable."""
    for sub in ("", "probes", "extraction"):
        path = str(NARCBENCH / sub)
        if path not in sys.path:
            sys.path.insert(0, path)


def probe_module():
    """NARCBench's `reproduce_LR` module (probe training, scores, evaluation)."""
    _add_paths()
    import reproduce_LR

    return reproduce_LR


def extraction_module():
    """NARCBench's `extract_core` module (chat rendering, run loading, hooks)."""
    _add_paths()
    import extract_core

    return extract_core


def model_layers(name: str, num_hidden_layers: int) -> list[int]:
    """Their default probe layers: `config.MODEL_LAYERS`, else the middle five layers."""
    _add_paths()
    import config

    return config.default_layers(name, num_hidden_layers)
