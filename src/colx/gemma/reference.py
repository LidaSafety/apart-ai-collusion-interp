"""Check our Gemma readout against the pinned jacobian-lens library (GPU; plan step 5).

On one real round-4 prompt, at layer 41 and the last prompt token:
1. the library's `JacobianLens.apply` (its own Gemma 3 wrapper, `from_hf`) gives reference
   logits, and its recorder gives the layer-41 activation;
2. our hook on block 41 must give the same activation (cosine >= 0.999), so both mean
   "output of block 41";
3. our readout, unembed(h @ J.T) in fp32, must share >= 23 of the top 25 printable tokens.
Gemma ties lm_head to the input embedding, so it can't be cast to fp32 for the library as on
Qwen; the library's unembed runs in bf16, hence the overlap threshold, not exact equality.
"""

import json
import sys
from pathlib import Path

import torch

from colx import provenance
from colx.gemma.calls import load_calls
from colx.gemma.extract import forward_points, read_points
from colx.gemma.model import LAYERS, Unembed, load
from colx.jlens.lens import load_maps
from colx.jlens.render import printable_mask, top_tokens

CHECK_LAYER = 41
MIN_OVERLAP = 23


def _library():
    """Import the pinned library from its submodule (read-only, not installed)."""
    sys.path.insert(0, str(Path("third_party/jacobian-lens").resolve()))
    from jlens.hf import from_hf
    from jlens.hooks import ActivationRecorder
    from jlens.lens import JacobianLens

    return JacobianLens, from_hf, ActivationRecorder


def check(model_dir: Path, lens_path: Path, core_dir: Path) -> dict:
    """Run the comparison on the first final call of the first run; return the verdicts."""
    jacobian_lens, from_hf, recorder_cls = _library()
    tokenizer, model = load(model_dir)
    run = sorted(p for p in core_dir.iterdir() if p.is_dir())[0]
    call = next(c for c in load_calls(run) if c["phase"] == "final")
    ids, _ = read_points(tokenizer, dict(call, reply=""), None)
    wrapped = from_hf(model, tokenizer)
    lens = jacobian_lens.load(str(lens_path))
    prompt = tokenizer.decode(ids)
    ref_logits, _, ref_ids = lens.apply(
        wrapped, prompt, layers=[CHECK_LAYER], positions=[-1], max_seq_len=16384
    )
    with recorder_cls(wrapped.layers, at=[CHECK_LAYER]) as rec, torch.no_grad():
        wrapped.forward(ref_ids)
        lib_h = rec.activations[CHECK_LAYER][0, -1].float()
    ours_h = forward_points(
        model, ref_ids[0].tolist(), {"start": ref_ids.shape[-1] - 1, "end": 0, "p2": -1}
    )
    layer_pos = (CHECK_LAYER,)
    our_h = ours_h[0, LAYERS.index(CHECK_LAYER)].float()
    jmap = load_maps(lens_path, layer_pos)[CHECK_LAYER].to(model.device)
    ours = Unembed(model)(our_h.to(model.device) @ jmap.T).cpu()
    ref = ref_logits[CHECK_LAYER][0].float().cpu()
    mask = printable_mask(tokenizer, ref.shape[-1])
    ref_top, our_top = set(top_tokens(ref, mask).tolist()), set(top_tokens(ours, mask).tolist())
    cos = torch.nn.functional.cosine_similarity(lib_h.cpu(), our_h, dim=0).item()
    return {
        "layer": CHECK_LAYER,
        "prompt_tokens": int(ref_ids.shape[-1]),
        "same_prompt_tokens": ref_ids[0].tolist() == ids,
        "activation_cosine": cos,
        "top25_overlap": len(ref_top & our_top),
        "max_abs_logit_diff": float((ref - ours).abs().max()),
        "passes": cos >= 0.999 and len(ref_top & our_top) >= MIN_OVERLAP,
        "reference_top25": [tokenizer.decode([i]) for i in top_tokens(ref, mask).tolist()],
    }


def write_check(model_dir: Path, lens_path: Path, core_dir: Path, out_dir: Path) -> dict:
    """Run the check and save `reference_check.json` with provenance."""
    result = check(model_dir, lens_path, core_dir)
    path = out_dir / "reference_check.json"
    path.write_text(
        json.dumps(
            provenance.collect("col lens-judge gemma check-lens", result=result),
            indent=1,
            default=str,
            ensure_ascii=False,
        )
    )
    return result
