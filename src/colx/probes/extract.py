"""Gemma activations with NARCBench's own extraction recipe (GPU; amendment 4).

Per agent call: render system + user + response with their `_build_gen_text`, tokenize
exactly as they do (`tokenizer(text, return_tensors="pt")`, special tokens included), run
one forward pass and keep the last token's output of each target decoder layer through
their `ActivationHooks`. Calls with an empty response get a zero vector, as in their code.
Runs come from their `load_runs`, so prompts and responses are paired their way.
"""

import io
import time
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import torch

from colx.backends import BACKENDS
from colx.probes.data import save_set
from colx.probes.narc import extraction_module

META_KEYS = ("run_id", "scenario_id", "scenario_domain", "mode", "agent_name", "role",
             "phase", "channel", "round")  # fmt: skip


def select_samples(runs_dir: Path, phases: tuple[str, ...], modes: tuple[str, ...]) -> list:
    """Their samples for the public calls of the given phases and run modes."""
    ec = extraction_module()
    with redirect_stdout(io.StringIO()):  # their loader prints a distribution table
        samples = ec.load_runs(runs_dir)
    return [
        s for s in samples
        if s["channel"] == "public" and s["phase"] in phases and s["mode"] in modes
    ]  # fmt: skip


def extract_samples(model, tokenizer, samples: list, layers: list[int], log=print) -> tuple:
    """Their gen-mode extraction over `samples`: (metadata list, layer arrays)."""
    ec = extraction_module()
    hooks = ec.ActivationHooks(model, layers)
    acts = {layer: [] for layer in layers}
    meta, start = [], time.time()
    try:
        for i, sample in enumerate(samples):
            if not sample["response"]:
                for layer in layers:
                    acts[layer].append(np.zeros(_hidden_size(model), dtype=np.float32))
            else:
                text = ec._build_gen_text(tokenizer, sample)
                ids = tokenizer(text, return_tensors="pt")["input_ids"].to(model.device)
                with torch.no_grad():
                    model(ids)
                captured = hooks.get_and_clear()
                for layer in layers:
                    acts[layer].append(captured[layer].numpy())
            meta.append({k: sample[k] for k in META_KEYS})
            if (i + 1) % 200 == 0:
                log(f"  {i + 1}/{len(samples)} calls ({time.time() - start:.0f}s)")
    finally:
        hooks.remove()
    return meta, {f"layer_{layer}": np.stack(v) for layer, v in acts.items()}


def _hidden_size(model) -> int:
    """Residual width (text config for multimodal Gemma)."""
    cfg = model.config
    return getattr(cfg, "hidden_size", None) or cfg.text_config.hidden_size


def extract_gemma(model_dir: Path, sets: dict, layers: list[int], out_dir: Path, log=print) -> dict:
    """Extract every set {name: (runs_dir, phases, modes)}; save each in their format."""
    tokenizer, model = BACKENDS["gemma"].load(model_dir)
    counts = {}
    for name, (runs_dir, phases, modes) in sets.items():
        samples = select_samples(runs_dir, phases, modes)
        log(f"{name}: {len(samples)} calls")
        meta, arrays = extract_samples(model, tokenizer, samples, layers, log)
        save_set(meta, arrays, out_dir / name)
        counts[name] = len(meta)
    return counts
