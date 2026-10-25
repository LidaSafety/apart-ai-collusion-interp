"""Fetch kitft's Gemma-3-27B NLA verbalizer and store it in bf16 (it ships in fp32, 108 GB).

One fp32 shard at a time: download to `tmp_dir`, cast every tensor to bf16, write to
`out_dir` under the same name, delete the fp32 copy. The small files (config, tokenizer,
`nla_meta.yaml`) are copied as they are, with the config's dtype set to bfloat16.
"""

import json
from pathlib import Path

from huggingface_hub import hf_hub_download, snapshot_download
from safetensors.torch import load_file, save_file

REPO = "kitft/nla-gemma3-27b-L41-av"
SMALL = ["*.json", "*.yaml", "*.jinja", "*.model", "tokenizer*", "NOTICE", "README.md"]


def convert(out_dir: Path, tmp_dir: Path, log=print) -> int:
    """Write the bf16 checkpoint to `out_dir`; return the number of shards."""
    snapshot_download(REPO, local_dir=out_dir, allow_patterns=SMALL)
    config = json.loads((out_dir / "config.json").read_text())
    config["torch_dtype"] = "bfloat16"
    (out_dir / "config.json").write_text(json.dumps(config, indent=2))
    shards = sorted(
        set(
            json.loads((out_dir / "model.safetensors.index.json").read_text())[
                "weight_map"
            ].values()
        )
    )
    for n, name in enumerate(shards):
        path = Path(hf_hub_download(REPO, name, local_dir=tmp_dir))
        tensors = {k: v.bfloat16().contiguous() for k, v in load_file(str(path)).items()}
        save_file(tensors, str(out_dir / name), metadata={"format": "pt"})
        path.unlink()
        log(f"shard {n + 1}/{len(shards)}")
    return len(shards)
