"""Read the stored discussion turns through the lens and save the token table (GPU or CPU).

Outputs under `results/discussion-turns/`:
- `turns_index.parquet`: one row per discussion call (run, agent, round, shard row);
- `turns_tokens.parquet`: raw and words-relative top-25 tokens per call, position, layer.
"""

from pathlib import Path

from colx import provenance, qwen
from colx.jlens.lens import LAYERS, load_maps, sha256_of
from colx.turns.stored import TURN_POSITIONS, load_turns
from colx.turns.tokens import token_table
from colx.unembed import from_checkpoint


def write_tokens(
    extract_dir: Path, model_dir: Path, lens_path: Path, out_dir: Path, device: str, log=print
) -> dict:
    """Check the lens hash, read the turns, compute both renderings, save with provenance."""
    digest = sha256_of(lens_path)
    if digest != provenance.LENS_SHA256:
        raise ValueError(f"lens sha256 {digest} != expected {provenance.LENS_SHA256}")
    out_dir.mkdir(parents=True, exist_ok=True)
    index, resid = load_turns(extract_dir, log)
    log(f"loaded {tuple(resid.shape)}")
    maps = {layer: m.to(device) for layer, m in load_maps(lens_path).items()}
    unembed = from_checkpoint(model_dir, device=device)
    table = token_table(index, resid, maps, unembed, qwen.load_tokenizer(str(model_dir)), log)
    meta = provenance.collect(
        "col lens-judge turns tokens",
        extract_dir=str(extract_dir),
        positions=TURN_POSITIONS,
        layers=LAYERS,
    )
    for name, frame in (("turns_index", index), ("turns_tokens", table)):
        frame.to_parquet(out_dir / f"{name}.parquet", index=False)
        provenance.write_meta(out_dir / f"{name}.parquet", meta)
    return {"calls": len(index), "token rows": len(table)}
