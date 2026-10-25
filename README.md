# Reading Exclusive Context from Activations: A Label-Free Monitor for Colluding LLM Agents

Submission to the **Apart Research AI Collusion Research Sprint** (Oct 23–25, 2026), Track 2 (Detection and Audit), with Track 3 stress tests.

**Read the report: [`docs/sprint/latex/report.pdf`](docs/sprint/latex/report.pdf)**

> [!IMPORTANT]
> **What predates the sprint.** This builds on the team's earlier SPAR Fall 2026 work, as the sprint rules allow. Everything up to the git tag **`pre-sprint`** (commit `d2eb0af`, Oct 22, 2026, 10:16 PM ET) is pre-existing; everything after it was done during the sprint (Oct 24–25). Commit hashes and dates match the project's private SPAR repository. The work was AI-assisted (Claude Code); the team is responsible for every claim. Details are in [What predates the sprint](#what-predates-the-sprint).

## The project

LLM agents that secretly coordinate against the people they serve can keep their messages innocuous, so monitors that read what agents *say* can miss them. We ask whether the coalition shows up in what the agents *represent* instead.

We read each agent's residual stream through a **J-lens** (Jacobian lens), which maps an activation to the tokens the model represents. Two agents given the same secret should carry concepts the others lack. Our monitor counts the lens entries that exactly two agents share and the other two lack. It needs no labels, no training and no LLM judge, and it points at the pair.

We test it on [NARCBench](https://github.com/aaronrose227/narcbench), a benchmark of committees where some runs contain an instructed coalition. We compare it with text-based monitors and with the benchmark's own trained deception probes. Pre-registered stress tests probe its limits, and we audit the benchmark's steganography tier. Every planned test was committed to a dated plan in `docs/plans/` before it ran.

The report has the results, figures, limitations and dual-use considerations.

## What predates the sprint

- **Pre-existing** (tag `pre-sprint`):
  - the repository scaffolding (uv, the `col` CLI, CI, pinned submodules);
  - the round-4 lens judge (`docs/results/round4-judge/`) and the loader, extraction, J-lens and statistics code it used;
  - Qwen3-32B NARCBench Core and Transfer transcripts with stored activations.
- **During the sprint:** everything else, including the overlap monitor, its baselines, the Gemma replication, the stress tests, the stego audit, the reproduction of NARCBench's probes, and every plan and result in `docs/`.
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

GPU steps (generation, extraction, lens readout) need one 80 GB GPU. Transcripts, activations and token tables are not in git; each results README in `docs/results/` names the files and commands behind every number, and every run records its seed, library versions and commits.

## Layout

```
src/colx/       one folder per experiment, plus shared loaders, lens and statistics code
tests/          unit tests, mirroring src/colx
docs/plans/     pre-registered plans with dated amendments
docs/results/   detailed results per experiment
docs/sprint/    the report (LaTeX and PDF) and its figures
third_party/    NARCBench and jacobian-lens (pinned, read-only)
```
