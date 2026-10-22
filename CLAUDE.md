# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## What this project is

Experiment code for a SPAR Fall 2026 project on **multi-agent collusion in LLM agents**:
when agents coordinate against the party they serve, can we detect it, how fragile is it,
and what breaks it. We build on existing collusion benchmarks (pinned under `third_party/`)
and evaluate detection and intervention methods against strong behavioural and text-level
baselines.

Research notes, literature maps, and write-ups live outside this repo. This repo holds only
code, configs, and tests.

## The prime directive: the researcher must understand the code

This is a research codebase for a small team. The researcher must be able to follow every
step. Optimize for readability over cleverness:

- Write code that a reader can verify against the paper or method it implements.
- Explain *research* decisions in docstrings: what an experiment does and why, in plain terms.
- When you make a non-obvious choice (a hyperparameter, a tensor shape, a layer index), state
  the reason in one comment or docstring line.
- Prefer a small, boring solution over a smart one. Elegance here means simplicity.

## Research reporting standards

- Every result is labelled **exploratory** unless it followed a plan written before the run.
- Seed all randomness explicitly and record seeds, library versions, and pinned
  `third_party/` commits in the output.

## Transparency when running experiments

The researcher must always be able to see what is running, what it is doing, and where its
output goes — in real time, not after the fact:

- **Announce before you run.** Before launching any experiment, training run, download, or
  long-running script, tell the researcher what you are about to execute, the exact command,
  and roughly how long it should take.
- **Every run writes a log file.** Redirect stdout+stderr of every experiment or script run
  to a `.log` file under `results/logs/`, named `<timestamp>_<command>.log`
  (e.g. `results/logs/2026-10-05T14-30_fetch.log`):

  ```sh
  mkdir -p results/logs
  uv run col fetch 2>&1 | tee "results/logs/$(date +%Y-%m-%dT%H-%M)_fetch.log"
  ```

- **Tell the researcher where the log is, immediately**, and give them the follow command,
  e.g.:

  > Logs are being written to `results/logs/2026-10-05T14-30_fetch.log` — follow live with:
  > `tail -f results/logs/2026-10-05T14-30_fetch.log`

- **Report progress and surprises.** Say when a run starts, finishes, or fails; report the
  outcome faithfully (including partial failures and skipped steps) with the relevant log
  lines. Never let a failure pass silently or summarise it away.
- Log files are working artifacts: they stay out of git (`*.log` is gitignored) but are
  referenced by path from any findings they support.

## Code standards

- Python >= 3.11, type hints on all public functions.
- Small units: one function does one thing, stated in its docstring's first line.
  Keep functions short (aim under ~30 lines); split when a function grows a second purpose.
- Small files: one module holds one concern. Split a module before it passes ~200-300 lines.
- Prefer pure functions. Isolate I/O, GPU work, and randomness at the edges so the core
  logic is unit-testable without a GPU.
- Use `pathlib.Path`, not `os.path` strings.
- No dead code, no commented-out code, no `TODO` without an owner and a reason.
- **Never modify, lint, or format anything under `third_party/`** — those are pinned
  submodules of other people's code; ruff excludes them by configuration. Reference their
  code read-only (e.g. `third_party/narcbench/...`).

## CLI

The `col` command (`src/colx/cli.py`, typer) is the front door to every experiment:

- Every new capability gets a `col` subcommand with a descriptive name; nothing important
  is runnable only as a script.
- Commands stay thin: parse arguments, call one library function in `colx`, print the result
  with `rich`. No research logic in the CLI module.
- Give each command clear `--help` text, sensible defaults, and readable output.

## Layout

```
src/colx/        package code (tests mirror it one to one)
tests/           pytest suite
third_party/     pinned submodules of external benchmarks/code (read-only)
data/            downloaded datasets and weights (gitignored)
results/         experiment outputs (gitignored; small summary files may be committed)
```

Keep `tests/` a mirror of `src/colx/`: `foo.py` → `tests/test_foo.py`.

## Testing

- Write unit tests alongside every new function or class, in the mirrored test file.
- Mark expensive tests so CI can skip them: `slow`, `gpu`. CI runs
  `pytest -m "not gpu and not slow"`.
- Test behavior, not implementation: assert on outputs and shapes, not on internal calls.
- Use small fixed arrays / tiny fake models in unit tests; real models belong under `gpu`.

## Quality gates (run before every commit)

```sh
uv run ruff format .           # format
uv run ruff check --fix .      # lint
uv run pytest                  # tests
```

All must pass clean. Do not silence a warning with an inline disable unless the tool is
wrong; when you must, add the reason on the same line. Pre-commit hooks enforce formatting
and commit style (`uv run pre-commit install --hook-type commit-msg --hook-type pre-commit`
after cloning).

### Before every push and every PR: reproduce CI locally

Run exactly what `.github/workflows/ci.yml` runs, each command bare — never pipe a gate
(`| tail`, `| grep`), because a pipe replaces the command's exit code with the pipe's:

```sh
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pytest -m "not gpu and not slow"
```

Push only when all of them pass. After you push or open a PR, wait for the pipeline
(`gh pr checks <n> --watch`) and report the PR as ready only when it is green. If it fails,
read the log (`gh run view <id> --log-failed`), fix, and repeat. Keep this list in sync
with `ci.yml` when the workflow changes.

## Workflow

- Environment: `uv` only. `uv sync` to install, `uv run <cmd>` to execute. Never `pip install`.
- Clone with `--recurse-submodules` (or run `git submodule update --init` after cloning).
- Commits follow Conventional Commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, ...).
  A commit-msg hook rejects other formats. On push to `main`, python-semantic-release bumps
  the version and writes `CHANGELOG.md` — never edit `CHANGELOG.md` or the version by hand.
- **Branch model:** see the table below. Never push changes directly to `main`, `development`
  or an `experiments/<series>/dev` branch; everything lands by PR.
- **Few PRs, clear commits:** one branch per experiment, built as a sequence of small
  Conventional Commits (one logical step each, tests in the same commit), merged with a
  **merge commit** so every step stays readable in the history. Do not squash.
- Commit scopes follow the package area (`narcbench`, `extract`, `jlens`, `judge`,
  `analysis`, `app`, `cli`, `deps`, `results`); omit the scope for repo-wide changes.

### Branches and merges

| Branch | Role | PR into | Merge type |
|---|---|---|---|
| `main` | releases (python-semantic-release on push) | — | — |
| `development` | all finished work | `main` | merge commit |
| `experiments/<series>/dev` | integration branch of one experiment series | `development` | merge commit |
| `experiments/<series>/<experiment>` | **one whole experiment**, step by step in commits | `experiments/<series>/dev` | **merge commit** |
| `feat/<slug>`, `fix/<slug>` | infrastructure outside any series | `development` | squash |

- Branch names are descriptive slugs; tracker codes (e.g. `E1`, `W1.3`) stay out of branch names.
- Never squash a long-lived branch (`*/dev`, `development`) into its target: squashing leaves
  the source history behind and every later promotion re-shows old changes and conflicts.
- Delete an experiment branch after it is merged.

**Current series: `lens-judge`** (integration branch `experiments/lens-judge/dev`, from
`development`). It is written from scratch and is independent of the earlier
`experiments/narcbench/*` code: do not import, copy or port code from those branches. Raw
inputs (NARCBench transcripts, stored activations) may be reused. First experiment:
`experiments/lens-judge/round4-judge`. An LLM judge reads each agent's J-lens tokens at the
final-round prompt end, and an AUROC tests whether its scores separate collusion runs from
the rest.
- Experiment outputs go to `results/` (gitignored). Code, configs, and tests are committed;
  large artifacts, datasets, and model weights are not.
