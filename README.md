# Reading collusion from activations: a label-free lens monitor for hidden coalitions

> [!IMPORTANT]
> **Disclosure: what was done before and during the sprint.** This project builds on the team's earlier work in a SPAR Fall 2026 project on multi-agent collusion, as the sprint rules allow. Everything up to the git tag **`pre-sprint`** (commit `d2eb0af`, Oct 22, 2026, 10:16 PM ET) is **pre-existing**; everything after it was done **during the sprint (Oct 24–25, 2026)**. Commit hashes and dates are identical to the project's private SPAR repository. The work was AI-assisted (Claude Code); the team is responsible for every claim.

### Pre-existing (before Oct 23, 2026)

- **Repo scaffolding** (Oct 5): uv project, the `col` typer CLI, CI, the pinned NARCBench submodule.
- **The round-4 lens judge** (Oct 22): an LLM judge reads one agent's J-lens tokens at a time. It was a **null result** (near chance), reported in `docs/results/round4-judge/`. Its code is the base the sprint built on:
  - `src/colx/narcbench/` (transcript loader and labels), `extract/` (activation extraction), `jlens/` (J-lens readout), `judge/` (the per-agent judge), `analysis/` (AUROC, bootstrap and shuffle statistics), `app/` (results explorer);
  - `qwen.py`, `unembed.py`, `provenance.py`, `cli_lens_judge.py`;
  - plans `docs/plans/round4-judge.md`, `round4-lens-diagnostic.md`, and `docs/notes/round4-step2-issues/`.
- **Data from an earlier project phase:** NARCBench Core and Transfer transcripts generated with Qwen3-32B, and their stored Qwen3-32B activations.
- **External, unmodified:** [NARCBench](https://github.com/aaronrose227/narcbench) and [`anthropics/jacobian-lens`](https://github.com/anthropics/jacobian-lens) (pinned submodules in `third_party/`), and Neuronpedia's J-lenses for Qwen3-32B and Gemma-3-27B-IT.

### Done during the sprint (Oct 24–25, 2026)

- **The overlap monitor** (the main result): first found during the sprint, in the joint-judge follow-up (`src/colx/joint/`).
- **New experiments and their code:** joint judge (`joint/`), discussion turns and a frozen text judge (`turns/`), the Gemma-3-27B replication with a new NARCBench Core generation (`gemma/`, `backends.py`), NARCBench-Stego with two leak fixes and three new datasets (`stego/`), Transfer (`transfer/`), the private-channel turn (`private/`), NLA readouts (`nla/`), J-lens vs J++ lens on Qwen3-4B (`lenscmp/`), and lens vs text overlap plus four stress-test conditions (`overlap/`). All with their CLI commands and tests.
- **Small changes to pre-existing code** (+89/−9 lines): a pooled lens rendering (`jlens/pooled.py`, new), `judge/run.py`, `narcbench/labels.py`, `cli_lens_judge.py`, and options in `gemma/`.
- **All other plans and results** in `docs/plans/` and `docs/results/`, including the series report.
- **New data:** Gemma-3-27B Core transcripts, three Gemma stego sets, a Qwen3-4B Core set, four stress-test sets, and every activation readout behind the results.

Check it yourself:

```sh
git log --oneline pre-sprint            # pre-existing work
git log --oneline pre-sprint..HEAD      # sprint work
git diff --stat pre-sprint HEAD         # everything added or changed during the sprint
```

Submission to the **Apart Research AI Collusion Research Sprint** (Oct 23–25, 2026), Track 2 (Detection and Audit), with a Track 3 stress test (colluders who know they are watched).

Every number traces to a result file and a log.

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
