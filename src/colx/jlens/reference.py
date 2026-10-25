"""Check our J-lens readout against the authors' library (third_party/jacobian-lens, GPU).

On one real round-4 prompt, at layer 39 and the last prompt token (P1):
1. `JacobianLens.apply` from the pinned library gives the reference lens logits;
2. our readout of the same forward pass's block-39 output must give the same top-25
   printable tokens, with logits within fp32 tolerance;
3. the stored block-39 residual must match the library's recorded layer-39 activation
   (cosine ≥ 0.999), confirming that both mean "output of block 39".

The library's unembed casts to the model's dtype; to compare in fp32 we put the final norm
and lm_head in fp32 for this check (the block outputs are unaffected).
"""

import json
import sys
from pathlib import Path

import pandas as pd
import torch
from safetensors.torch import load_file

from colx import provenance, qwen
from colx.jlens.lens import load_maps, readout
from colx.jlens.render import printable_mask, top_tokens
from colx.narcbench.runs import join_final_prompt
from colx.unembed import from_model

CHECK_LAYER = 39
LOGIT_ATOL = 1e-2
REFERENCE_DIR = Path("third_party/jacobian-lens")


def _reference_library():
    """Import the pinned library from its submodule folder (read-only, not installed)."""
    sys.path.insert(0, str(REFERENCE_DIR.resolve()))
    from jlens.hf import from_hf
    from jlens.hooks import ActivationRecorder
    from jlens.lens import JacobianLens

    return JacobianLens, from_hf, ActivationRecorder


def _first_prompt(out_dir: Path) -> tuple[str, pd.Series]:
    """The round-4 user prompt of the first agent of the first run, and its agent row."""
    agents = pd.read_parquet(out_dir / "agents.parquet")
    runs = pd.read_parquet(out_dir / "runs.parquet").set_index("run_id")
    agent = agents.iloc[0]
    run = runs.loc[agent["run_id"]]
    user = join_final_prompt(run["brief"], run["discussion"], run["request"])
    return user, agent


def compare(model_path: str, lens_path: Path, out_dir: Path) -> dict[str, object]:
    """Run the reference check; return the numbers and verdicts."""
    jacobian_lens, from_hf, activation_recorder = _reference_library()
    tokenizer, model = qwen.load_tokenizer(model_path), qwen.load_model(model_path)
    model.model.norm.float()
    model.lm_head.float()
    user, agent = _first_prompt(out_dir)
    prompt = qwen.render_chat(tokenizer, agent["system_prompt"], user)
    wrapped = from_hf(model, tokenizer)
    lens = jacobian_lens.load(str(lens_path))
    ref_logits, _, ref_ids = lens.apply(
        wrapped, prompt, layers=[CHECK_LAYER], positions=[-1], max_seq_len=16384
    )
    with activation_recorder(wrapped.layers, at=[CHECK_LAYER]) as recorder, torch.no_grad():
        wrapped.forward(ref_ids)
        fresh = recorder.activations[CHECK_LAYER][0, -1].detach()
    jmap = load_maps(lens_path, (CHECK_LAYER,))[CHECK_LAYER].to(fresh.device)
    ours = readout(fresh, jmap, from_model(model)).cpu()
    stored = load_file(str(out_dir / "activations.safetensors"))["resid"][0, 0, CHECK_LAYER]
    return _verdicts(ref_logits[CHECK_LAYER][0], ours, fresh.cpu(), stored, tokenizer, ref_ids)


def _verdicts(ref, ours, fresh, stored, tokenizer, ref_ids) -> dict[str, object]:
    """Compare reference vs our logits and top-25 tokens, and stored vs fresh activation."""
    mask = printable_mask(tokenizer, ref.shape[-1])
    ref_top, our_top = top_tokens(ref, mask), top_tokens(ours, mask)
    max_diff = (ref - ours).abs().max().item()
    cos = torch.nn.functional.cosine_similarity(stored.float(), fresh.float(), dim=-1).item()
    return {
        "layer": CHECK_LAYER,
        "prompt_tokens": int(ref_ids.shape[-1]),
        "same_top25_tokens": bool(torch.equal(ref_top, our_top)),
        "max_abs_logit_diff": max_diff,
        "logits_within_tolerance": max_diff <= LOGIT_ATOL,
        "stored_vs_library_cosine": cos,
        "stored_block_index_matches": cos >= 0.999,
        "reference_top25": [tokenizer.decode([int(i)]) for i in ref_top],
    }


def write_reference_check(model_path: str, lens_path: Path, out_dir: Path) -> dict[str, object]:
    """Run the check and save `reference_check.json` with provenance."""
    result = compare(model_path, lens_path, out_dir)
    path = out_dir / "reference_check.json"
    record = provenance.collect("col lens-judge check-lens", result=result)
    path.write_text(json.dumps(record, indent=2, default=str) + "\n")
    return result
