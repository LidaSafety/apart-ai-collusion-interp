import json
from pathlib import Path

import torch
from safetensors.torch import save_file

from colx.unembed import LM_HEAD_KEY, NORM_KEY, Unembed, from_checkpoint


def _weights() -> tuple[torch.Tensor, torch.Tensor]:
    torch.manual_seed(0)
    return torch.rand(4) + 0.5, torch.randn(6, 4)


def test_unembed_is_rmsnorm_then_lm_head() -> None:
    norm, head = _weights()
    unembed = Unembed(norm_weight=norm, eps=1e-6, lm_head=head)
    h = torch.randn(3, 4, dtype=torch.bfloat16)
    x = h.float()
    expected = (norm * x / torch.sqrt(x.pow(2).mean(-1, keepdim=True) + 1e-6)) @ head.T
    out = unembed(h)
    assert out.dtype == torch.float32
    torch.testing.assert_close(out, expected)


def test_from_checkpoint_reads_sharded_weights(tmp_path: Path) -> None:
    norm, head = _weights()
    save_file({NORM_KEY: norm}, str(tmp_path / "a.safetensors"))
    save_file({LM_HEAD_KEY: head.to(torch.bfloat16)}, str(tmp_path / "b.safetensors"))
    index = {"weight_map": {NORM_KEY: "a.safetensors", LM_HEAD_KEY: "b.safetensors"}}
    (tmp_path / "model.safetensors.index.json").write_text(json.dumps(index))
    (tmp_path / "config.json").write_text(json.dumps({"rms_norm_eps": 1e-6}))
    unembed = from_checkpoint(tmp_path)
    assert unembed.eps == 1e-6
    torch.testing.assert_close(unembed.lm_head, head.to(torch.bfloat16).float())
