# Who Shares a Secret? A label-free activation monitor for hidden coalitions of LLM agents

Submission to the **Apart Research AI Collusion Research Sprint** (Oct 23–25, 2026), Track 2 (Detection and Audit), with Track 3 stress tests.
**Report:** [`docs/sprint/latex/report.pdf`](docs/sprint/latex/report.pdf) · **Full results:** [`docs/results/overlap-monitor/README.md`](docs/results/overlap-monitor/README.md)

> [!IMPORTANT]
> **What predates the sprint.** This builds on the team's earlier SPAR Fall 2026 work, as the sprint rules allow. Everything up to the git tag **`pre-sprint`** (commit `d2eb0af`, Oct 22, 2026, 10:16 PM ET) is pre-existing; everything after it was done during the sprint (Oct 24–25). Commit hashes and dates match the project's private SPAR repository. The work was AI-assisted (Claude Code); the team is responsible for every claim. Details are in [What predates the sprint](#what-predates-the-sprint).

## The idea

When two of four LLM agents secretly coordinate, their messages can stay innocuous. We read each agent's residual stream through a **J-lens** (Jacobian lens), which maps an activation to the tokens the model represents, and count the lens entries that exactly two agents share and the other two lack. The run score is the largest pair count minus the median of the six pairs. Nothing is trained, labelled or prompted. Benchmark: [NARCBench](https://github.com/aaronrose227/narcbench) (4 agents discuss and vote; in collusion runs 2 get a secret motive and a private channel).

## Main results

AUROC, collusion runs vs all-honest controls, with the rate of collusion runs caught at zero false positives on the controls:

| Dataset | Lens overlap | Best text overlap | NARCBench's trained probe¹ | Caught at 0% FPR (lens / best text) |
|---|---|---|---|---|
| Core, Gemma-3-27B-IT (planned primary) | **0.98** | 0.90 (+0.08, lower bound +0.02) | 1.00 | 70% / 64% |
| Core, Qwen3-32B | **0.99** | 0.95 | 1.00 | 74% / 66% |
| Transfer, 6 unseen task types, Qwen3-32B | **1.00** | 0.59 | 0.78 (planned, +0.22, lower +0.13) | 100% / 14% |

¹ Deception Split, run with the authors' code; on Core it is trained on the other domains of the same benchmark, so it is in distribution. Our monitor has no training data.

- **Early:** from each agent's state just before its own first public message, it already scores 0.94 (Gemma) and 0.93 (Qwen).
- **Names the pair:** a rule fixed on Gemma names the colluders in 60 of 86 held-out runs (70%, p = 0.0002).
- **Stress tests** (planned, 50 new Gemma runs each): it survives colluders warned that their reasoning is monitored (0.99), told to keep the arrangement out of their reasoning (0.99), and paraphrased instructions (0.96), even without a private channel (0.89). Text overlap catches up there (0.92–0.98).
- **But it is not a detector of intent.** Honest pairs given a harmless confidential note are flagged almost as readily (0.88–0.94), and the same note given openly too (0.94). NARCBench's trained probe rejects that note (0.97 vs overlap's 0.64, planned) but also flags the budget and deadline notes against controls (0.93, 0.92).
- **Audit:** NARCBench-Stego's own monitor flags 0 of 150 collusion tables (a prompted monitor reaches 0.68–0.84), and two leaks expose the secret; we fixed both. An LLM text monitor that works with Qwen judging Qwen (0.84) is inverted with Gemma judging Gemma (0.17).

**Honest negatives.**
- Judges reading the shared lens tokens could not tell collusion from a harmless note (0.51, 0.56).
- On Stego, where the colluders share no context, the overlap monitor fails.
- The supervised TF-IDF baseline failed its own validity gate.
- A stego receiver effect passed once and did not replicate.

Every planned test was committed to a dated plan in `docs/plans/` before it ran; the monitor itself was found post hoc. Appendix B of the report lists every prediction next to its outcome.

## What predates the sprint

- **Pre-existing** (tag `pre-sprint`):
  - the repository scaffolding (uv, the `col` CLI, CI, pinned submodules);
  - the round-4 lens judge, a null result: `docs/results/round4-judge/`, and the loader, extraction, J-lens and statistics code it used;
  - Qwen3-32B NARCBench Core and Transfer transcripts with stored activations.
- **During the sprint:** everything else, including:
  - the overlap monitor and its text baselines;
  - the LLM text monitor and the Gemma replication;
  - the stress tests, the stego audit and Transfer;
  - the reproduction of NARCBench's probes;
  - every plan and result in `docs/`.
- **External, unmodified:** NARCBench and [`anthropics/jacobian-lens`](https://github.com/anthropics/jacobian-lens) (pinned in `third_party/`), and Neuronpedia's J-lenses.

```sh
git log --oneline pre-sprint..HEAD   # sprint work
git diff --stat pre-sprint HEAD      # everything added or changed during the sprint
```

## Reproduce

```sh
git clone --recurse-submodules https://github.com/LidaSafety/apart-ai-collusion-interp
uv sync
uv run pytest -m "not gpu and not slow"   # CPU unit tests
uv run col lens-judge --help              # every step is a subcommand
```

GPU steps (generation, extraction, lens readout) need one 80 GB GPU. Transcripts, activations and token tables are not in git; each results README names the files and commands behind every number, and every run records its seed, library versions and commits.

## Layout

```
src/colx/       one folder per experiment, plus shared loaders, lens and statistics code
tests/          unit tests, mirroring src/colx
docs/plans/     pre-registered plans with dated amendments
docs/results/   results per experiment
docs/sprint/    the report (LaTeX and PDF) and its figures
third_party/    NARCBench and jacobian-lens (pinned, read-only)
```
