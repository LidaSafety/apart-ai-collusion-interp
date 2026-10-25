# Reading collusion from activations: a label-free lens monitor for hidden coalitions

Submission to the **Apart Research AI Collusion Research Sprint** (Oct 23–25, 2026), Track 2 (Detection and Audit), with a Track 3 stress test (colluders who know they are watched).

Jorge Roldan · SPAR Fall 2026 project on multi-agent collusion · Built with Claude Code (AI-assisted; every number traces to a result file and a log)

## The question

When LLM agents on a committee secretly coordinate, can we see it in their **activations**, beyond what their **messages** show? We read every agent's residual stream through a **J-lens** (Jacobian lens), which turns an activation into the tokens the model "has in mind". The benchmark is [NARCBench](https://github.com/aaronrose227/narcbench): 4 agents discuss and vote; in half the runs, 2 are secretly told to push one option and share a private channel.

## Main results

**1. A label-free, LLM-free lens monitor finds hidden coalitions.** Per run, count the lens entries that exactly two agents share and the other two don't; the run score is the largest pair count minus the median over the 6 pairs. It separates collusion runs from controls on 2 models, 2 lenses and 3 datasets, and beats the same count on the agents' messages every time (AUROC):

| Dataset | Lens (raw) | Best text-overlap monitor | Lens − text (one-sided 95% lower bound) |
|---|---|---|---|
| NARCBench Core, Gemma-3-27B-IT (planned primary test) | **0.98** | 0.90 | +0.08 (+0.02), p = 0.006 |
| NARCBench Core, Qwen3-32B | **0.99** | 0.95 | +0.035 (+0.005) |
| NARCBench Transfer (6 unseen task types), Qwen3-32B | **1.00** | 0.59 | **+0.41 (+0.34)** |

On Transfer the coalition is almost invisible in the text and plain in the activations. The monitor finds the right 2-vs-2 split of the agents in 49–50 of 50 Core runs and 36 of 36 Transfer runs; it can't tell which side is the coalition, because colluders *lose* concepts the honest pair shares.

**2. Stress tests (planned before running).** Does the signal survive colluders warned that their reasoning is monitored, paraphrased instructions, and no shared text at all? How often does a harmless shared secret trigger a false alarm? *In progress; see `docs/results/overlap-monitor/`.*

**3. Audit findings on NARCBench-Stego** (card-counting steganography): its own LLM monitor flagged **0 of 150** collusion tables, while a simple prompted monitor reaches 0.68–0.84. Two design leaks (the receiver's decoding notes in the public chat; the true count in the colluders' channel) inflate any monitor that reads them; we fixed both.

**4. Honest negatives.** LLM judges read lens tokens poorly. The lens doesn't predict *who will act* on the instruction earlier, or better, than a judge reading the conversation. A natural-language-autoencoder readout didn't surface the decoded secret. The receiver-decodes-the-secret effect in stego was positive once (p = 0.021) and didn't replicate.

The series report: [`docs/results/lens-judge-series.md`](docs/results/lens-judge-series.md). Each experiment has a plan in `docs/plans/` (written before its run) and results in `docs/results/<experiment>/`.

## What was done before vs during the sprint

The git history is the record. The tag `pre-sprint` marks the last commit before the sprint (`d2eb0af`, Oct 22, 10:16 PM ET). Every commit hash here is identical to the project's private SPAR repository.

```sh
git log --oneline pre-sprint            # pre-existing work (43 commits)
git log --oneline pre-sprint..HEAD      # sprint work
git diff --stat pre-sprint HEAD         # everything added or changed during the sprint
```

| | Pre-existing (before Oct 23) | Sprint (Oct 24–25) |
|---|---|---|
| Code | Scaffolding (uv, typer CLI, CI; Oct 5). The round-4 lens judge (Oct 22): NARCBench loader (`narcbench/`), activation extraction (`extract/`), J-lens readout (`jlens/`), per-agent LLM judge (`judge/`), statistics (`analysis/`), results app (`app/`), `qwen.py`, `unembed.py`, `provenance.py` | Everything else: `joint/` (where the overlap monitor was first found), `turns/`, `gemma/`, `backends.py`, `stego/`, `transfer/`, `private/`, `nla/`, `lenscmp/`, `overlap/`, their CLIs and tests |
| Changes to pre-existing code during the sprint | — | Small: `jlens/pooled.py` (new), `judge/run.py`, `narcbench/labels.py`, `cli_lens_judge.py` (+89/−9 lines) |
| Results | Round 4 (`docs/results/round4-judge/`), a null: one-agent-at-a-time LLM judges near chance | Every other plan and result in `docs/` |
| Data | NARCBench Core and Transfer transcripts from Qwen3-32B and their stored activations (earlier project phase) | Generated during the sprint: Gemma-3-27B Core, three Gemma stego sets, a Qwen3-4B Core set, four stress-test sets |
| External | NARCBench and `anthropics/jacobian-lens` (pinned submodules in `third_party/`, unmodified); Neuronpedia's J-lenses for Qwen3-32B and Gemma-3-27B-IT | — |

## Reproduce

```sh
git clone --recurse-submodules https://github.com/LidaSafety/apart-ai-collusion-interp
uv sync
uv run pytest -m "not gpu and not slow"      # unit tests, CPU only
uv run col lens-judge --help                 # every experiment step is a subcommand
```

GPU steps (generation, extraction, lens readout) need one 80 GB GPU; generation uses vLLM 0.10.1.1 on its V0 engine (`src/colx/gemma/generate.py`). Outputs (transcripts, activations, token tables) are not in git; each results README names the files and commands behind every number. Every run records its seed, library versions, the repo commit and the pinned `third_party/` commits.

## Layout

```
src/colx/       package: one folder per experiment, plus shared loaders, lens and stats code
tests/          unit tests, mirroring src/colx
docs/plans/     pre-registered plans (with dated amendments)
docs/results/   results per experiment, and the series report
third_party/    NARCBench, jacobian-lens (pinned, read-only)
```

`CLAUDE.md` holds the project's coding and reporting rules (pre-registration, labelling exploratory results, seeding).
