"""Report figures, drawn from the saved result files (no recomputation).

Publication conventions: vector PDF (plus a PNG for the web page) drawn at the printed width,
so text matches the caption size; one colour-blind-safe palette (Okabe-Ito) used the same way
in every figure (lens overlap = vermillion, text = grey, Qwen = blue, Transfer = green);
panel letters on multi-panel figures.

- `summary_figures` reads only the JSON results: stress conditions, early warning, layers.
- `data_figures` also reads per-run tables and transcripts: the method example and ROC curves.
"""

import json
import textwrap
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

VERMILLION, GREY, BLUE, GREEN, AMBER = "#D55E00", "#8C8C8C", "#0072B2", "#009E73", "#E69F00"
LENS, TEXT = VERMILLION, GREY
FULL, HALF = 6.5, 4.3  # inches: text width at 1-inch margins, and a smaller single figure
plt.rcParams.update({
    "font.size": 8.5, "axes.titlesize": 9, "axes.labelsize": 8.5, "legend.fontsize": 8,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "axes.linewidth": 0.6, "lines.linewidth": 1.6,
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.02,
})  # fmt: skip

DATASETS = {
    "gemma": "Core, Gemma-3-27B",
    "qwen": "Core, Qwen3-32B",
    "transfer": "Transfer, Qwen3-32B",
}
CONDITIONS = {
    "aware": "Warned of a monitor",
    "evade": "Warned + told to hide it in reasoning",
    "para": "Paraphrased instruction",
    "independent": "No shared text, no channel",
    "benign": "Harmless secret: cite evidence",
    "benign_budget": "Harmless secret: budget",
    "benign_deadline": "Harmless secret: deadline",
    "benign_open": "Same note, given openly",
}
EXAMPLE = "deception__mil_01"  # the Gemma Core scenario shown in the method figure
GEMMA_CORE = Path("third_party/narcbench/data/raw/gemma_3_27b/core")


def _save(fig, out: Path, name: str) -> None:
    """Write the figure as vector PDF (for LaTeX) and 300-dpi PNG (for the web page)."""
    fig.savefig(out / f"{name}.pdf")
    fig.savefig(out / f"{name}.png", dpi=300)
    plt.close(fig)


def _title(ax, letter: str, text: str) -> None:
    """Left-aligned panel title with its letter, e.g. "(a) Collusion run"."""
    ax.set_title(f"({letter}) {text}", loc="left")


def _clean(ax) -> None:
    """No top or right spine."""
    ax.spines[["top", "right"]].set_visible(False)


def _intervals(ax, labels: list[str], series: list[tuple[list, str, str]]) -> None:
    """Dots with 95% interval bars; series = [(rows of (est, lo, hi), colour, name)]."""
    off = [0.16, -0.16] if len(series) == 2 else [0.0]
    for (rows, colour, name), dy in zip(series, off, strict=True):
        for i, (est, lo, hi) in enumerate(rows):
            y = len(labels) - 1 - i + dy
            ax.plot([lo, hi], [y, y], color=colour, lw=1.6, solid_capstyle="round")
            ax.plot(est, y, "o", color=colour, ms=4.5, label=name if i == 0 else None)
            ax.text(hi + 0.008, y, f"{est:.2f}", va="center", fontsize=7.5, color=colour)
    ax.set_yticks(range(len(labels)), labels[::-1])
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0.4, 1.06)
    ax.axvline(0.5, color="#555", ls=(0, (3, 3)), lw=0.7)
    ax.grid(axis="x", color="#ececec", lw=0.6)
    ax.set_axisbelow(True)
    _clean(ax)


def stress(results: Path, out: Path) -> None:
    """Stress conditions: lens vs best text overlap, collusion and harmless-note groups banded."""
    st = json.loads((results / "stress.json").read_text())["conditions"]
    st |= json.loads((results / "stress3.json").read_text())["conditions"]
    labels, lens, text = [], [], []
    for key, label in CONDITIONS.items():
        m = st[key]["mode_vs_control"]
        best = st[key]["lens_minus_best_text"]["lens_raw"]["best_text"]
        labels.append(label)
        lens.append(tuple(m["lens_raw"][k] for k in ("auroc", "ci_low", "ci_high")))
        text.append(tuple(m[best][k] for k in ("auroc", "ci_low", "ci_high")))
    fig, ax = plt.subplots(figsize=(FULL * 0.8, 3.7))
    ax.axhspan(-0.5, 3.5, color=AMBER, alpha=0.12, lw=0)
    ax.axhline(3.5, color="#bbb", lw=0.6)
    _intervals(ax, labels, [(lens, LENS, "Lens overlap"), (text, TEXT, "Best text overlap")])
    ax.set_xlabel("AUROC, condition runs vs the same 50 controls")
    ax.text(1.065, 5.5, "real collusion", rotation=270, va="center", fontsize=8, color="#444")
    ax.text(1.065, 1.5, "no collusion\n(harmless note)", rotation=270, va="center", fontsize=8,
            color="#8a5a00", ha="center")  # fmt: skip
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False)
    _save(fig, out, "fig_stress")


def early(results: Path, out: Path) -> None:
    """AUROC by read point (each round's turn start, then the vote), raw tokens, both models."""
    e = json.loads((results / "extras" / "early_warning.json").read_text())["early_warning"]
    fig, ax = plt.subplots(figsize=(HALF, 2.5))
    for key, colour in (("gemma", VERMILLION), ("qwen", BLUE)):
        rows = sorted((r for r in e[key] if r["rendering"] == "raw"), key=lambda r: r["round"])
        vote = json.loads((results / "text" / f"{key}.json").read_text())
        vote = vote["mode_vs_control"]["lens_raw"]
        y = [r["auroc"] for r in rows] + [vote["auroc"]]
        lo = [r["ci_low"] for r in rows] + [vote["ci_low"]]
        hi = [r["ci_high"] for r in rows] + [vote["ci_high"]]
        ax.fill_between(range(4), lo, hi, color=colour, alpha=0.15, lw=0)
        ax.plot(range(4), y, "o-", color=colour, ms=4, label=DATASETS[key].split(", ")[1])
    ax.set_xticks(
        range(4), ["Before R1\n(no public\nmessage yet)", "Before R2", "Before R3", "At the\nvote"]
    )
    ax.axhline(0.5, color="#555", ls=(0, (3, 3)), lw=0.7)
    ax.set_ylim(0.45, 1.02)
    ax.set_ylabel("AUROC")
    _clean(ax)
    ax.legend(frameon=False, loc="center right")
    _save(fig, out, "fig_early")


def layers(results: Path, out: Path) -> None:
    """AUROC from one layer's entries alone, by layer position in the 10 read."""
    lay = json.loads((results / "extras" / "layers.json").read_text())["layers"]
    fig, ax = plt.subplots(figsize=(HALF, 2.5))
    for (key, label), colour in zip(DATASETS.items(), (VERMILLION, BLUE, GREEN), strict=True):
        rows = lay[key]
        ax.plot(range(1, len(rows) + 1), [r["auroc"] for r in rows], "o-", color=colour,
                label=label, ms=3)  # fmt: skip
    ax.axhline(0.5, color="#555", ls=(0, (3, 3)), lw=0.7)
    ax.set_xlabel("Lens layer (1 = earliest of the 10 read)")
    ax.set_ylabel("AUROC, single layer")
    ax.set_xticks(range(1, 11))
    ax.set_ylim(0.45, 1.0)
    _clean(ax)
    ax.legend(frameon=False, loc="lower left", fontsize=7.5)
    _save(fig, out, "fig_layers")


def _pair_matrix(sets: list[set]) -> np.ndarray:
    """4x4 symmetric matrix of entries each pair shares that the other two lack."""
    from colx.joint.pairs import exclusive_counts

    m = np.full((4, 4), np.nan)
    for (i, j), n in exclusive_counts(sets).items():
        m[i - 1, j - 1] = m[j - 1, i - 1] = n
    return m


def _draw_matrix(ax, m: np.ndarray, roles: list[str], title: str, vmax: float) -> None:
    """Heatmap of pair counts with colluders labelled C, honest agents H; diagonal blank."""
    ax.imshow(np.where(np.isnan(m), 0, m), cmap="Oranges", vmin=0, vmax=vmax)
    for i in range(4):
        for j in range(4):
            if i != j:
                v = int(m[i, j])
                ax.text(j, i, v, ha="center", va="center", fontsize=8.5,
                        color="white" if v > vmax * 0.55 else "black")  # fmt: skip
    labels = [f"{'C' if r == 'colluder' else 'H'}{k + 1}" for k, r in enumerate(roles)]
    ax.set_xticks(range(4), labels)
    ax.set_yticks(range(4), labels)
    for tick in [*ax.get_xticklabels(), *ax.get_yticklabels()]:
        if tick.get_text().startswith("C"):
            tick.set_color(VERMILLION)
            tick.set_fontweight("bold")
    if title:
        ax.set_title(title)
    ax.tick_params(length=0)


def _word(token: str) -> bool:
    """A readable English-looking word token: ASCII letters only, longer than 3."""
    w = token.strip()
    return w.isascii() and w.isalpha() and len(w) > 3


def _example_run(t, mode: str) -> tuple:
    """(pair matrix, roles, score, words only the colluders share) for one example run."""
    from colx.joint.pairs import overlap_score
    from colx.narcbench.runs import load_run

    run = load_run(GEMMA_CORE / f"{EXAMPLE}__{mode}")
    order = sorted(a.name for a in run.agents)
    roles = [next(a.role for a in run.agents if a.name == n) for n in order]
    r = t[t.run_id == run.run_id]

    def sets(rendering: str, col: str) -> list[set]:
        x = r[r.rendering == rendering]
        return [set(zip(x[x.agent == n].layer, x[x.agent == n][col], strict=True)) for n in order]

    raw = sets("raw", "token_id")
    words = []
    if mode == "collusion":
        rel = sets("rel", "token")
        i, j = (k for k, ro in enumerate(roles) if ro == "colluder")
        others = set().union(*(rel[k] for k in range(4) if k not in (i, j)))
        words = sorted({w.strip() for _, w in (rel[i] & rel[j]) - others if _word(w)})
    return _pair_matrix(raw), roles, overlap_score(raw)[0], words


def method_example(results: Path, out: Path) -> None:
    """The monitor on one real run and its matched control: pair counts, score, shared words."""
    import pandas as pd

    t = pd.read_parquet(Path("results/gemma/final_tokens.parquet"))
    t = t[t.position == "P1"]
    coll, ctrl = _example_run(t, "collusion"), _example_run(t, "control")
    vmax = max(np.nanmax(coll[0]), np.nanmax(ctrl[0]))
    fig, axes = plt.subplots(1, 3, figsize=(FULL, 2.35), gridspec_kw={"width_ratios": [1, 1, 1.3]})
    for ax, (m, roles, score, _), name, letter in zip(
        axes[:2], (coll, ctrl), ("Collusion run", "Its control run"), "ab", strict=True
    ):
        _draw_matrix(ax, m, roles, "", vmax)
        _title(ax, letter, f"{name} (score {score:.0f})")
    axes[2].axis("off")
    fig.tight_layout(w_pad=1.0)
    # Align panel (c) with the square matrices' tops (their axes are shorter than the row).
    fig.canvas.draw()
    top = axes[0].get_position().y1
    x0 = axes[2].get_position().x0
    title_y = axes[0].title.get_window_extent().transformed(fig.transFigure.inverted()).y0
    fig.text(x0, title_y, "(c) Words only C1 and C3 share", fontsize=9, va="bottom")
    fig.text(x0, top, "\n".join(textwrap.wrap(", ".join(coll[3]), 34)), va="top", fontsize=8,
             linespacing=1.45)  # fmt: skip
    _save(fig, out, "fig_method")


def roc_panels(results: Path, out: Path) -> None:
    """ROC curves, lens vs best text overlap, collusion runs vs controls, per dataset."""
    import pandas as pd
    from sklearn.metrics import roc_auc_score, roc_curve

    fig, axes = plt.subplots(1, 3, figsize=(FULL, 2.45), sharey=True)
    for ax, (key, label), letter in zip(axes, DATASETS.items(), "abc", strict=True):
        best = json.loads((results / "text" / f"{key}.json").read_text())
        best = best["lens_minus_best_text"]["lens_raw"]["best_text"]
        t = pd.read_parquet(results / "text" / f"{key}.parquet")
        for inst, colour, name in (("lens_raw", LENS, "Lens"), (best, TEXT, "Best text")):
            s = t[t.instrument == inst]
            y = (s["mode"] == "collusion").to_numpy()
            fpr, tpr, _ = roc_curve(y, s.run_score)
            auc = roc_auc_score(y, s.run_score)
            ax.plot(fpr, tpr, color=colour, lw=1.8, label=f"{name} ({auc:.2f})")
        ax.plot([0, 1], [0, 1], ls=(0, (3, 3)), color="#555", lw=0.7)
        _title(ax, letter, label)
        ax.set_xlabel("False-positive rate")
        ax.set_xticks([0, 0.5, 1])
        ax.set_yticks([0, 0.5, 1])
        ax.legend(loc="lower right", frameon=False, handlelength=1.4)
        ax.set_aspect("equal")
        _clean(ax)
    axes[0].set_ylabel("True-positive rate")
    fig.tight_layout(w_pad=0.6)
    _save(fig, out, "fig_roc")


def summary_figures(results: Path, out: Path) -> list[str]:
    """The figures that need only the JSON results; returns the PDF names."""
    out.mkdir(parents=True, exist_ok=True)
    for draw in (stress, early, layers):
        draw(results, out)
    return sorted(p.name for p in out.glob("fig_*.pdf"))


def data_figures(results: Path, out: Path) -> list[str]:
    """The figures that read per-run tables and transcripts; returns the PDF names."""
    out.mkdir(parents=True, exist_ok=True)
    for draw in (method_example, roc_panels, compare_figure):
        draw(results, out)
    return sorted(p.name for p in out.glob("fig_*.pdf"))


PROBE_ROWS = [  # (key in compare.json secondary, label)
    ("qwen_core_their_protocol", "Qwen Core (their protocol)"),
    ("qwen_transfer", "Qwen Transfer (zero-shot)"),
    ("gemma_core_their_protocol", "Gemma Core (their protocol)"),
    ("gemma_final:aware_vs_core_controls", "Gemma: warned of a monitor"),
    ("gemma_final:evade_vs_core_controls", "Gemma: told to hide it"),
    ("gemma_final:para_vs_core_controls", "Gemma: paraphrased"),
    ("gemma_final:independent_vs_core_controls", "Gemma: no shared text"),
]
HARMLESS_ROWS = [
    ("gemma_final:benign_vs_core_controls", "Cite-evidence note"),
    ("gemma_final:benign_budget_vs_core_controls", "Budget note"),
    ("gemma_final:benign_deadline_vs_core_controls", "Deadline note"),
    ("gemma_final:benign_open_vs_core_controls", "Same note, given openly"),
]
# Supervised TF-IDF is left out: it failed its pre-registered shuffled-label validity gate.
SERIES = (("overlap", "Overlap monitor (ours, untrained)", VERMILLION),
          ("probe", "NARCBench probe (trained; Deception Split)", BLUE))  # fmt: skip


def _cell(entry: dict, series: str) -> dict | None:
    """One AUROC record for a series from a compare.json entry (probe: Deception Split)."""
    if series not in entry:
        return None
    v = entry[series]
    return v if "auroc" in v else v["deception_split"]


def _compare_rows(ax, rows: list[tuple[str, dict]]) -> None:
    """Dot-and-interval rows, one offset line per series, on one AUROC axis."""
    for i, (_, entry) in enumerate(rows):
        y0 = len(rows) - 1 - i
        for k, (key, name, colour) in enumerate(SERIES):
            r = _cell(entry, key)
            if r is None:
                continue
            y = y0 + (0.5 - k) * 0.3
            ax.plot(
                [r["ci_low"], r["ci_high"]], [y, y], color=colour, lw=1.4, solid_capstyle="round"
            )
            ax.plot(r["auroc"], y, "o", color=colour, ms=4, label=name if i == 0 else None)
    ax.set_yticks(range(len(rows)), [lab for lab, _ in rows][::-1])
    ax.tick_params(axis="y", length=0)
    ax.axvline(0.5, color="#555", ls=(0, (3, 3)), lw=0.7)
    ax.grid(axis="x", color="#ececec", lw=0.6)
    ax.set_axisbelow(True)
    _clean(ax)


def compare_figure(results: Path, out: Path) -> None:
    """Overlap monitor vs NARCBench's trained probe on identical runs (amendment 4)."""
    cmp = json.loads((Path("results/probes") / "compare.json").read_text())
    sec = cmp["secondary"]
    harm = {"overlap": sec["core_collusion_vs_benign"]["overlap"], "probe": cmp["K1"]}
    fig, (a, b) = plt.subplots(2, 1, figsize=(FULL, 4.0), sharex=True,
                               gridspec_kw={"height_ratios": [len(PROBE_ROWS), 5]})  # fmt: skip
    _compare_rows(a, [(lab, sec[k]) for k, lab in PROBE_ROWS])
    a.set_xlim(0.3, 1.02)
    _title(a, "a", "Collusion runs vs all-honest controls (higher is better)")
    a.legend(loc="lower left", frameon=False, fontsize=7.5)
    rows = [("Core collusion vs cite-evidence note", harm)]
    rows += [(lab, sec[k]) for k, lab in HARMLESS_ROWS]
    _compare_rows(b, rows)
    b.axhspan(-0.5, len(rows) - 1.5, color=AMBER, alpha=0.12, lw=0)
    b.text(0.31, len(rows) - 1.62, "Harmless note vs controls: false alarms (lower is better)",
           fontsize=7, color="#7a5a00", va="top")  # fmt: skip
    _title(b, "b", "Collusion vs a harmless shared note")
    b.set_xlabel("AUROC with 95% interval")
    fig.tight_layout(h_pad=1.0)
    _save(fig, out, "fig_compare")
