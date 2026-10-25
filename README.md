# spar-collusion-experiments

Experiments on multi-agent collusion in LLM agents: detection, fragility, and countermeasures.

- **Package:** `colx` · **CLI:** `col`
- **Upstream:** [`aaronrose227/narcbench`](https://github.com/aaronrose227/narcbench) is pinned as the `third_party/narcbench/` git submodule; released data comes from HF `aaronrose227/narcbench` into `data/` (gitignored).

## Results

- **Sprint report:** [`docs/sprint/latex/report.pdf`](docs/sprint/latex/report.pdf), *Reading Exclusive Context from Activations: A Label-Free Monitor for Colluding LLM Agents* (Apart AI Collusion Research Sprint, Oct 2026).
- **Per experiment:** `docs/results/<experiment>/README.md`, each with its pre-registered plan in `docs/plans/`. The series overview is [`docs/results/lens-judge-series.md`](docs/results/lens-judge-series.md).

## Setup

```bash
git clone --recurse-submodules git@github.com:LidaSafety/spar-collusion-experiments.git
cd spar-collusion-experiments
uv sync
uv run pre-commit install --hook-type commit-msg --hook-type pre-commit
uv run col info
```

## Conventions

- **Conventional commits** enforced at commit time (`feat:`, `fix:`, `docs:`, `chore:`, …).
- **CHANGELOG.md and versions are automatic**: python-semantic-release runs on every push to `main` (`.github/workflows/release.yml`) and derives the version bump and changelog entries from commit messages — never edit `CHANGELOG.md` or the version by hand.
- CI runs ruff + pytest on PRs and main.
- Analyses live in `src/colx/` and are exposed as `col` subcommands.
- Everything under `data/`, `results/**/*.npz`, and model weight shards stays out of git.
