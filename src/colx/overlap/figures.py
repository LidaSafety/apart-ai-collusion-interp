"""Static figures for the sprint report, drawn from the saved result files (no recomputation).

1. lens vs best text overlap per dataset (part 1);
2. stress conditions, lens and best text with 95% intervals (part 2);
3. early warning by round, both models (amendment A);
4. per-layer AUROC (amendment C).
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

LENS, TEXT = "#c0562f", "#9a9a9a"
DATASETS = {
    "gemma": "Core, Gemma-3-27B",
    "qwen": "Core, Qwen3-32B",
    "transfer": "Transfer, Qwen3-32B",
}
CONDITIONS = {
    "aware": "Warned of a monitor",
    "para": "Paraphrased instruction",
    "independent": "No shared text, no channel",
    "benign": "Harmless shared secret",
}


def _style(ax, xlabel: str) -> None:
    """Shared axis styling: light grid, no top/right spines, chance line."""
    ax.axvline(0.5, color="#555", ls="--", lw=0.8)
    ax.grid(axis="x", color="#e5e5e5")
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlabel(xlabel)


def _intervals(ax, labels: list[str], series: list[tuple[list, str, str]]) -> None:
    """Dots with interval bars; series = [(rows of (est, lo, hi), colour, name)]."""
    off = [0.15, -0.15] if len(series) == 2 else [0.0]
    for (rows, colour, name), dy in zip(series, off, strict=True):
        for i, (est, lo, hi) in enumerate(rows):
            y = len(labels) - 1 - i + dy
            ax.plot([lo, hi], [y, y], color=colour, lw=2, solid_capstyle="round")
            ax.plot(est, y, "o", color=colour, label=name if i == 0 else None)
            ax.text(hi + 0.01, y, f"{est:.2f}", va="center", fontsize=11)
    ax.set_yticks(range(len(labels)), labels[::-1])
    ax.set_xlim(0.4, 1.09)


def text_vs_lens(results: Path, out: Path) -> None:
    """Figure 1: AUROC of the lens and the best text overlap per dataset."""
    labels, lens, text = [], [], []
    for key, label in DATASETS.items():
        j = json.loads((results / "text" / f"{key}.json").read_text())
        m, best = j["mode_vs_control"], j["lens_minus_best_text"]["lens_raw"]["best_text"]
        labels.append(label)
        lens.append(tuple(m["lens_raw"][k] for k in ("auroc", "ci_low", "ci_high")))
        text.append(tuple(m[best][k] for k in ("auroc", "ci_low", "ci_high")))
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    _intervals(ax, labels, [(lens, LENS, "Lens overlap"), (text, TEXT, "Best text overlap")])
    _style(ax, "AUROC, collusion runs vs controls")
    ax.legend(loc="lower left", frameon=False)
    fig.tight_layout()
    fig.savefig(out / "fig1_lens_vs_text.png", dpi=200, bbox_inches="tight")


def stress(results: Path, out: Path) -> None:
    """Figure 2: stress conditions, lens and best text with intervals."""
    st = json.loads((results / "stress.json").read_text())["conditions"]
    labels, lens, text = [], [], []
    for key, label in CONDITIONS.items():
        m = st[key]["mode_vs_control"]
        best = st[key]["lens_minus_best_text"]["lens_raw"]["best_text"]
        labels.append(label)
        lens.append(tuple(m["lens_raw"][k] for k in ("auroc", "ci_low", "ci_high")))
        text.append(tuple(m[best][k] for k in ("auroc", "ci_low", "ci_high")))
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    _intervals(ax, labels, [(lens, LENS, "Lens overlap"), (text, TEXT, "Best text overlap")])
    _style(ax, "AUROC, condition runs vs the same 50 controls")
    ax.legend(loc="lower left", frameon=False)
    fig.tight_layout()
    fig.savefig(out / "fig2_stress.png", dpi=200, bbox_inches="tight")


def early(results: Path, out: Path) -> None:
    """Figure 3: AUROC by read point (round 1-3 turn start, then the vote), raw tokens."""
    e = json.loads((results / "extras" / "early_warning.json").read_text())["early_warning"]
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    for key, colour in (("gemma", LENS), ("qwen", "#2f6fc0")):
        rows = sorted((r for r in e[key] if r["rendering"] == "raw"), key=lambda r: r["round"])
        vote = json.loads((results / "text" / f"{key}.json").read_text())["mode_vs_control"][
            "lens_raw"
        ]
        y = [r["auroc"] for r in rows] + [vote["auroc"]]
        lo = [r["ci_low"] for r in rows] + [vote["ci_low"]]
        hi = [r["ci_high"] for r in rows] + [vote["ci_high"]]
        x = range(4)
        ax.fill_between(x, lo, hi, color=colour, alpha=0.15, lw=0)
        ax.plot(x, y, "o-", color=colour, label=DATASETS[key].split(", ")[1])
    ax.set_xticks(
        range(4), ["Before R1\n(no own message)", "Before R2", "Before R3", "At the vote"]
    )
    ax.axhline(0.5, color="#555", ls="--", lw=0.8)
    ax.set_ylim(0.45, 1.02)
    ax.set_ylabel("AUROC")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="lower left", bbox_to_anchor=(0, 1), ncol=2)
    fig.tight_layout()
    fig.savefig(out / "fig3_early_warning.png", dpi=200, bbox_inches="tight")


def layers(results: Path, out: Path) -> None:
    """Figure 4: AUROC from one layer's entries alone, by relative depth."""
    lay = json.loads((results / "extras" / "layers.json").read_text())["layers"]
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    for (key, label), colour in zip(DATASETS.items(), (LENS, "#2f6fc0", "#3a9a5b"), strict=True):
        rows = lay[key]
        ax.plot(
            range(1, len(rows) + 1),
            [r["auroc"] for r in rows],
            "o-",
            color=colour,
            label=label,
            ms=3,
        )
    ax.axhline(0.5, color="#555", ls="--", lw=0.8)
    ax.set_xlabel("Lens layer (1 = earliest of the 10 read)")
    ax.set_ylabel("AUROC, single layer")
    ax.set_ylim(0.45, 1.0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1), ncol=3)
    fig.tight_layout()
    fig.savefig(out / "fig4_layers.png", dpi=200, bbox_inches="tight")


def all_figures(results: Path, out: Path) -> list[str]:
    """Draw every figure into `out`; return the file names."""
    out.mkdir(parents=True, exist_ok=True)
    for draw in (text_vs_lens, stress, early, layers):
        draw(results, out)
    return sorted(p.name for p in out.glob("fig*.png"))
