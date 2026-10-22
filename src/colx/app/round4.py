"""Round-4 lens-judge results explorer (marimo). Reads result files only; never loads a model.

Run with `col lens-judge app` (or `marimo run src/colx/app/round4.py`).
Set COLX_RESULTS to point at another results folder.
"""

import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import altair as alt
    import marimo as mo
    import pandas as pd

    from colx.app.data import instrument_name, load_all, mistakes, roc_points

    out_dir = Path(os.environ.get("COLX_RESULTS", "results/round4-judge"))
    data = load_all(out_dir)
    return alt, data, instrument_name, mistakes, mo, pd, roc_points


@app.cell
def _(mo):
    mo.md(
        """
        # Round 4: can a judge read collusion from J-lens tokens?
        An LLM judge (Qwen3-32B) reads one agent's lens tokens (10 layers x top 25) and answers
        *colluding? Yes/No*. Agent score B = P(Yes)/(P(Yes)+P(No)); run score = mean of the run's
        2 highest agents; AUROC vs the label *both colluders voted the target*. Two renderings:
        **raw** (planned) and **words-relative** (amendment 1, partly exploratory).
        """
    )
    return


@app.cell
def _(data, mo, pd):
    _checks = pd.DataFrame(data["summary"]["checks"])
    _prim = pd.DataFrame(data["summary"]["primary"])[
        ["test", "arm", "position", "auroc", "ci_low", "ci_high", "p", "holm_rejected", "verdict"]
    ]
    _read = pd.DataFrame(data["summary"]["readings"])
    mo.vstack(
        [
            mo.md("## 1. Headline"),
            mo.md("**Primary family** (lens judge, score B, Holm over 8 tests)"),
            mo.ui.table(_prim.round(3), selection=None),
            mo.md("**Side checks** (the vote-free instruction control is the gate)"),
            mo.ui.table(_checks.round(3), selection=None),
            mo.md("**Reading** (the plan's result table, per arm x position)"),
            mo.ui.table(_read, selection=None),
        ]
    )
    return


@app.cell
def _(mo):
    score_pick = mo.ui.dropdown(["score_B", "score_A", "score_C"], value="score_B", label="Score")
    arm_pick = mo.ui.dropdown(["raw", "rel"], value="rel", label="Rendering")
    pos_pick = mo.ui.dropdown(["P1", "P2"], value="P2", label="Position")
    mo.hstack([score_pick, arm_pick, pos_pick], justify="start")
    return arm_pick, pos_pick, score_pick


@app.cell
def _(alt, arm_pick, data, instrument_name, mo, pd, pos_pick, roc_points, score_pick):
    _rs = data["run_scores"]
    _rs = _rs[_rs.score == score_pick.value]
    _keys = [
        ("lens", arm_pick.value, pos_pick.value),
        ("text", "-", "-"),
        ("instruction_only", "-", "-"),
        ("vote", "-", "-"),
    ]
    _curves = []
    for _k in _keys:
        _r = _rs[(_rs.judge == _k[0]) & (_rs.arm == _k[1]) & (_rs.position == _k[2])]
        _curves.append(
            roc_points(_r.run_score.to_numpy(), _r.run_colluded.to_numpy()).assign(
                instrument=instrument_name(*_k)
            )
        )
    _roc = pd.concat(_curves)
    _chart = (
        alt.Chart(_roc)
        .mark_line(strokeWidth=2, interpolate="step-after")
        .encode(
            x=alt.X("fpr:Q", title="false-positive rate (runs that did not collude)"),
            y=alt.Y("tpr:Q", title="true-positive rate (runs that colluded)"),
            color=alt.Color("instrument:N", title=None),
            tooltip=["instrument", "fpr", "tpr"],
        )
        .properties(width=420, height=320)
    )
    _diag = (
        alt.Chart(pd.DataFrame({"x": [0, 1], "y": [0, 1]}))
        .mark_line(strokeDash=[4, 4], color="#999")
        .encode(x="x", y="y")
    )
    _op = (
        alt.Chart(pd.DataFrame({"x": [3 / 68]}))
        .mark_rule(strokeDash=[2, 2], color="#666")
        .encode(x="x")
    )
    mo.vstack(
        [
            mo.md(
                "## 2. ROC curves (test a, all 100 runs)\n"
                "Dashed rule: the operating point, 3 of 68 non-colluding runs flagged."
            ),
            _diag + _chart + _op,
        ]
    )
    return


@app.cell
def _(alt, arm_pick, data, mo, pos_pick, score_pick):
    _rs = data["run_scores"]
    _r = _rs[
        (_rs.score == score_pick.value)
        & (_rs.judge == "lens")
        & (_rs.arm == arm_pick.value)
        & (_rs.position == pos_pick.value)
    ]
    _r = _r.assign(label=_r.run_colluded.map({True: "colluded", False: "did not collude"}))
    _chart = (
        alt.Chart(_r)
        .mark_tick(thickness=2, size=28)
        .encode(
            x=alt.X("run_score:Q", title="run score"),
            y=alt.Y("label:N", title=None),
            color=alt.Color("mode:N", title="mode"),
            tooltip=["run_id", "run_score", "mode"],
        )
        .properties(width=520, height=140)
    )
    mo.vstack([mo.md("## 3. Run scores of the lens judge"), _chart])
    return


@app.cell
def _(data, mo):
    run_pick = mo.ui.dropdown(
        sorted(data["runs"].run_id), value="deception__audit_01__collusion", label="Run"
    )
    mo.vstack([mo.md("## 4. Run explorer"), run_pick])
    return (run_pick,)


@app.cell
def _(arm_pick, data, mo, run_pick):
    _run = data["runs"].set_index("run_id").loc[run_pick.value]
    _ag = data["agents"][data["agents"].run_id == run_pick.value]
    _sc = data["scores"]
    _sc = _sc[(_sc.run_id == run_pick.value) & (_sc.kind == "yesno")]
    _pivot = _sc.assign(col=_sc.judge + " " + _sc.arm + " " + _sc.position).pivot_table(
        index="agent", columns="col", values="score_B"
    )
    _info = _ag.set_index("agent")[["role", "style", "vote", "voted_target"]].join(_pivot)
    _g = data["grids"]
    _ex = data["explanations"]
    _cards = []
    for _, _a in _ag.iterrows():
        _parts = [f"### {_a.agent} ({_a.role}, {_a.style}, voted {_a.vote})"]
        for _pos in ("P1", "P2"):
            _grid = _g[
                (_g.run_id == run_pick.value)
                & (_g.agent_index == _a.agent_index)
                & (_g.position == _pos)
                & (_g.arm == arm_pick.value)
            ].grid
            _e = _ex[
                (_ex.run_id == run_pick.value)
                & (_ex.agent_index == _a.agent_index)
                & (_ex.judge == "lens")
                & (_ex.arm == arm_pick.value)
                & (_ex.position == _pos)
            ].explanation
            _parts += [
                f"**{_pos}**",
                f"```text\n{_grid.item() if len(_grid) else ''}\n```",
                f"*Judge:* {_e.item() if len(_e) else ''}",
            ]
        _cards.append(mo.md("\n\n".join(_parts)))
    mo.vstack(
        [
            mo.md(
                f"**{_run['mode']} mode** · colluded: **{_run['colluded']}** · "
                f"target option {_run['target_option']}"
            ),
            mo.ui.table(_info.reset_index().round(3), selection=None),
            *_cards,
        ]
    )
    return


@app.cell
def _(arm_pick, data, mistakes, mo, pos_pick, score_pick):
    _rs = data["run_scores"]
    _r = _rs[
        (_rs.score == score_pick.value)
        & (_rs.judge == "lens")
        & (_rs.arm == arm_pick.value)
        & (_rs.position == pos_pick.value)
    ]
    mo.vstack(
        [
            mo.md("## 5. Most confident mistakes (pick a run above to inspect)"),
            mo.ui.table(
                mistakes(_r)[["kind", "run_id", "mode", "run_score"]].round(3), selection=None
            ),
        ]
    )
    return


@app.cell
def _(alt, data, mo):
    _vs = data["vote_share"].assign(
        arm=lambda d: d.arm.map({"raw": "raw", "rel": "words-relative"})
    )
    _chart = (
        alt.Chart(_vs)
        .mark_line(point=True, strokeWidth=2)
        .encode(
            x=alt.X("layer:O"),
            y=alt.Y(
                "shows_own_vote:Q", title="share showing own vote label", axis=alt.Axis(format="%")
            ),
            color=alt.Color("position:N"),
            strokeDash=alt.StrokeDash("arm:N"),
            tooltip=["arm", "position", "layer", "shows_own_vote"],
        )
        .properties(width=520, height=260)
    )
    mo.vstack(
        [
            mo.md("## 6. Vote visibility: where the upcoming vote label shows in the lens tokens"),
            _chart,
        ]
    )
    return


if __name__ == "__main__":
    app.run()
