import json
from pathlib import Path

from colx.overlap.figures import CONDITIONS, DATASETS, all_figures

AUC = {"auroc": 0.9, "ci_low": 0.8, "ci_high": 0.95}


def fake_results(root: Path) -> None:
    """The minimal result files the figures read."""
    (root / "text").mkdir(parents=True)
    (root / "extras").mkdir()
    for key in DATASETS:
        record = {"mode_vs_control": {"lens_raw": AUC, "text_words": AUC},
                  "lens_minus_best_text": {"lens_raw": {"best_text": "text_words"}}}  # fmt: skip
        (root / "text" / f"{key}.json").write_text(json.dumps(record))
    cond = {"mode_vs_control": {"lens_raw": AUC, "text_words": AUC},
            "lens_minus_best_text": {"lens_raw": {"best_text": "text_words"}}}  # fmt: skip
    (root / "stress.json").write_text(json.dumps({"conditions": dict.fromkeys(CONDITIONS, cond)}))
    early = [{"round": r, "rendering": "raw"} | AUC for r in (1, 2, 3)]
    (root / "extras" / "early_warning.json").write_text(
        json.dumps({"early_warning": {"gemma": early, "qwen": early}})
    )
    layers = [{"layer": i, "auroc": 0.8} for i in range(10)]
    (root / "extras" / "layers.json").write_text(
        json.dumps({"layers": dict.fromkeys(DATASETS, layers)})
    )


def test_all_figures_writes_four_pngs(tmp_path: Path) -> None:
    fake_results(tmp_path / "res")
    names = all_figures(tmp_path / "res", tmp_path / "out")
    assert len(names) == 4 and all((tmp_path / "out" / n).stat().st_size > 0 for n in names)
