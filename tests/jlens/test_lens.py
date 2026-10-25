from pathlib import Path

import torch

from colx.jlens.lens import LAYERS, load_maps, readout, sha256_of
from colx.unembed import Unembed


def test_layers_are_the_planned_ten() -> None:
    assert LAYERS == (24, 28, 32, 35, 39, 43, 47, 50, 54, 58)


def test_sha256_of(tmp_path: Path) -> None:
    path = tmp_path / "f"
    path.write_bytes(b"abc")
    assert sha256_of(path) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_load_maps_returns_fp32_requested_layers(tmp_path: Path) -> None:
    path = tmp_path / "lens.pt"
    torch.save({"J": {i: torch.eye(3, dtype=torch.float16) for i in range(4)}}, path)
    maps = load_maps(path, (1, 3))
    assert sorted(maps) == [1, 3]
    assert maps[1].dtype == torch.float32


def test_readout_is_unembed_of_transported_residual() -> None:
    torch.manual_seed(0)
    jmap, head = torch.randn(4, 4), torch.randn(5, 4)
    unembed = Unembed(norm_weight=torch.ones(4), eps=1e-6, lm_head=head)
    h = torch.randn(2, 4)
    torch.testing.assert_close(readout(h, jmap, unembed), unembed(h @ jmap.T))
