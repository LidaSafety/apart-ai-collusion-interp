"""Anatomy of the overlap monitor on one real run (report appendix figure).

The monitor sees each agent as a set of 250 (layer, token) lens entries. The figure shows,
on the method figure's example scenario:
(a) every entry grouped by exactly which agents hold it, so the six two-agent groups that
    the monitor counts stand out against everything it ignores;
(b) how the six pair counts become a run score (largest minus median), collusion run vs
    its all-honest control;
(c) in which layers the colluders' exclusive entries sit.
"""

from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from colx.overlap.figures import (
    EXAMPLE,
    FULL,
    GEMMA_CORE,
    GREY,
    VERMILLION,
    _clean,
    _save,
    _title,
)

LAYERS = (23, 27, 30, 34, 38, 41, 45, 49, 52, 56)  # the Gemma blocks read (Appendix I)
HONEST_PAIR = "#4d4d4d"
LIGHT = "#d9d9d9"


def membership_counts(sets: list[set]) -> dict[tuple[int, ...], int]:
    """Number of entries held by exactly each group of agents (agent indices, sorted)."""
    holders: dict = {}
    for i, s in enumerate(sets):
        for entry in s:
            holders.setdefault(entry, []).append(i)
    counts: dict[tuple[int, ...], int] = {}
    for who in holders.values():
        counts[tuple(who)] = counts.get(tuple(who), 0) + 1
    return counts


def all_groups(n: int) -> list[tuple[int, ...]]:
    """Every non-empty group of n agents, by size then index: singles, pairs, ..., all."""
    return [g for k in range(1, n + 1) for g in combinations(range(n), k)]


def exclusive_by_layer(sets: list[set], pair: tuple[int, int], layers) -> list[int]:
    """Per layer, the entries both agents of `pair` hold and no other agent holds."""
    i, j = pair
    others = set().union(*(s for k, s in enumerate(sets) if k not in pair))
    exclusive = (sets[i] & sets[j]) - others
    return [sum(1 for layer, _ in exclusive if layer == lay) for lay in layers]


def run_score(sets: list[set]) -> tuple[list[int], float]:
    """The six exclusive pair counts, and the run score: largest minus median."""
    counts = membership_counts(sets)
    pairs = [counts.get(p, 0) for p in combinations(range(len(sets)), 2)]
    return pairs, max(pairs) - float(np.median(pairs))


def _example_sets(mode: str) -> tuple[list[set], list[str]]:
    """Raw P1 entry sets of the example run's four agents, and their labels (C1, H2, ...)."""
    import pandas as pd

    from colx.narcbench.runs import load_run

    run = load_run(GEMMA_CORE / f"{EXAMPLE}__{mode}")
    order = sorted(a.name for a in run.agents)
    roles = [next(a.role for a in run.agents if a.name == n) for n in order]
    t = pd.read_parquet(Path("results/gemma/final_tokens.parquet"))
    t = t[(t.run_id == run.run_id) & (t.position == "P1") & (t.rendering == "raw")]
    sets = [set(zip(t[t.agent == n].layer, t[t.agent == n].token_id, strict=True)) for n in order]
    labels = [f"{'C' if r == 'colluder' else 'H'}{k + 1}" for k, r in enumerate(roles)]
    return sets, labels


def _group_colour(group: tuple[int, ...], labels: list[str]) -> str:
    """Colluder pair vermillion, honest pair dark grey, other pairs grey, the rest light."""
    if len(group) != 2:
        return LIGHT
    kinds = {labels[i][0] for i in group}
    return VERMILLION if kinds == {"C"} else HONEST_PAIR if kinds == {"H"} else GREY


def _upset(bars, dots, sets: list[set], labels: list[str]) -> None:
    """Panel (a): entry counts per exact group of holders, with a membership matrix."""
    counts, groups = membership_counts(sets), all_groups(len(sets))
    x = np.arange(len(groups))
    heights = [counts.get(g, 0) for g in groups]
    bars.bar(x, heights, color=[_group_colour(g, labels) for g in groups], width=0.7)
    for xi, h, g in zip(x, heights, groups, strict=True):
        if len(g) == 2:
            bars.text(xi, h + 4, str(h), ha="center", fontsize=6.5)
    bars.axvspan(3.5, 9.5, color="#f3f3f3", zorder=0, lw=0)
    top = max(heights) * 1.32
    bars.set_ylim(0, max(heights) * 1.36)
    bars.text(6.5, top, "counted:\nheld by exactly two", ha="center", va="top", fontsize=7)
    bars.text(1.5, top, "ignored:\none agent", ha="center", va="top", fontsize=7, color="#777")
    bars.text(12, top, "ignored:\nthree or four", ha="center", va="top", fontsize=7,
              color="#777")  # fmt: skip
    bars.set_xticks([])
    bars.set_ylabel("Lens entries")
    _clean(bars)
    for xi, g in zip(x, groups, strict=True):
        dots.scatter([xi] * len(labels), range(len(labels)), s=9, color=LIGHT, zorder=1)
        dots.scatter([xi] * len(g), list(g), s=11, color="#333", zorder=2)
        if len(g) > 1:
            dots.plot([xi, xi], [min(g), max(g)], color="#333", lw=0.8, zorder=1)
    dots.set_yticks(range(len(labels)), labels)
    dots.set_ylim(len(labels) - 0.5, -0.5)
    dots.set_xticks([])
    dots.spines[:].set_visible(False)
    dots.tick_params(length=0)


def _score_rows(ax, runs: list[tuple[str, list[set]]]) -> None:
    """Panel (b): the six pair counts per run, the median, the largest, and the score."""
    for y, (_name, sets) in enumerate(runs):
        pairs, score = run_score(sets)
        med = float(np.median(pairs))
        ax.scatter(pairs, [y] * len(pairs), s=14, color=GREY, zorder=2)
        ax.scatter([max(pairs)], [y], s=22, color=VERMILLION if y == 0 else "#333", zorder=3)
        ax.plot([med, med], [y - 0.25, y + 0.25], color="#333", lw=1.2)
        ax.annotate("", xy=(max(pairs), y - 0.32), xytext=(med, y - 0.32),
                    arrowprops={"arrowstyle": "->", "lw": 0.8})  # fmt: skip
        ax.text((med + max(pairs)) / 2, y - 0.4, f"score {score:.0f}", ha="center",
                va="bottom", fontsize=7)  # fmt: skip
    ax.set_yticks(range(len(runs)), [n for n, _ in runs])
    ax.set_ylim(len(runs) - 0.5, -0.8)
    ax.set_xlabel("Entries exclusive to a pair (6 pairs; | = median)")
    _clean(ax)


def _layer_bars(ax, sets: list[set], labels: list[str]) -> None:
    """Panel (c): the colluder and honest pairs' exclusive entries, layer by layer."""
    col = tuple(i for i, lab in enumerate(labels) if lab[0] == "C")
    hon = tuple(i for i, lab in enumerate(labels) if lab[0] == "H")
    x = np.arange(len(LAYERS))
    ax.bar(x - 0.2, exclusive_by_layer(sets, col, LAYERS), 0.4, color=VERMILLION,
           label="colluder pair")  # fmt: skip
    ax.bar(x + 0.2, exclusive_by_layer(sets, hon, LAYERS), 0.4, color=HONEST_PAIR,
           label="honest pair")  # fmt: skip
    ax.set_xticks(x, [str(lay) for lay in LAYERS], fontsize=7)
    ax.set_xlabel("Gemma block")
    ax.set_ylabel("Exclusive entries")
    ax.set_ylim(0, ax.get_ylim()[1] * 1.45)
    ax.legend(frameon=False, fontsize=7, loc="upper left", ncol=2)
    _clean(ax)


def anatomy_figure(out: Path) -> None:
    """The three-panel anatomy of the overlap monitor on the example run (fig_anatomy)."""
    coll, labels = _example_sets("collusion")
    ctrl, _ = _example_sets("control")
    fig = plt.figure(figsize=(FULL, 3.7))
    grid = fig.add_gridspec(2, 2, width_ratios=[1.35, 1], height_ratios=[3, 1.25],
                            hspace=0.08, wspace=0.32)  # fmt: skip
    bars, dots = fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[1, 0])
    _upset(bars, dots, coll, labels)
    _title(bars, "a", "Who holds each lens entry (collusion run)")
    right = grid[:, 1].subgridspec(2, 1, hspace=0.75)
    score_ax, layer_ax = fig.add_subplot(right[0]), fig.add_subplot(right[1])
    _score_rows(score_ax, [("collusion run", coll), ("its control", ctrl)])
    _title(score_ax, "b", "Six pair counts to one score")
    _layer_bars(layer_ax, coll, labels)
    _title(layer_ax, "c", "Where the exclusive entries sit")
    _save(fig, out, "fig_anatomy")
