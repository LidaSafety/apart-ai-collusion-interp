# Discussion turns: does follow-through show in the colluders' own turns?

2026-10-24 · Jorge Roldan (draft by Claude) · Plan: [`docs/plans/discussion-turns.md`](../../plans/discussion-turns.md), approved before any readout · Follows [the joint-judge results](../joint-judge/README.md)

**Labels.** The planned tests are *planned*. The two diagnostics under "Checks" were added after seeing the results, so they are *exploratory*.

## In short

1. **One primary test passes: round 3, T-start.** Just before a colluder writes its last discussion turn, a held-out lens-token classifier predicts whether it will vote the target at **0.73 [0.58, 0.87]** (p < 0.001; Holm over 6 read points).
   - It holds within instruction style (p = 0.001).
   - It beats a style-only baseline: +0.23, one-sided lower bound +0.06.
   - Raw tokens give 0.77 [0.62, 0.89].
   - This is the first lens readout in the series that carries follow-through beyond instruction wording.
2. **It is mostly a run-level signal, not a person-level one.** Runs where both colluders followed through score higher than runs where neither did. But in the 9 runs where one colluder followed and the other didn't, the classifier ranks the follower first only 4 times.
3. **The other 5 read points are not significant after correction** (0.46–0.63). Earlier rounds and the ends of the agents' own messages carry less.
4. **The text baseline is invalid** (0.27–0.30, below chance because of a cross-validation artifact; see "Checks"). So we cannot say whether the lens shows more than the agents' own words.

## Setup in one paragraph

**Data.** The 100 colluders of NARCBench Core (Qwen3-32B): 73 voted the target, 27 did not. Their stored residuals at their own discussion turns, rounds 1–3, at two positions:
- **T-start:** the prompt end before writing the turn;
- **T-end:** the last token of the agent's own message.

That gives 6 read points. No new forward passes were needed.

**Lens tokens.** The same lens and 10 layers as round 4, rendered two ways:
- **words-relative** (primary): relative to the 400 calls of the same round;
- **raw:** the top 25 printable tokens.

**Classifier.** Logistic regression on (layer, token) presence in each agent's top 25 (C = 0.1), held out by scenario in 10 folds (seed 0).

**Tests.** AUROC with 95% scenario-bootstrap intervals (10,000 draws) and shuffle p-values (10,000 shuffles).

**Baselines,** with the same classifier and folds:
- **style:** the instruction style and the run's style group;
- **text:** TF-IDF of the colluder's own messages up to that round.

## Primary family (words-relative classifier, follow-through, Holm)

| Read point | AUROC | 95% interval | p | Passes |
|---|---|---|---|---|
| Round 1, T-start | 0.59 | [0.41, 0.77] | 0.083 | no |
| Round 1, T-end | 0.46 | [0.35, 0.59] | 0.71 | no |
| Round 2, T-start | 0.63 | [0.46, 0.80] | 0.023 | no (Holm) |
| Round 2, T-end | 0.57 | [0.44, 0.70] | 0.14 | no |
| **Round 3, T-start** | **0.73** | **[0.58, 0.87]** | **< 0.001** | **yes** |
| Round 3, T-end | 0.57 | [0.40, 0.74] | 0.13 | no |

## Secondary tests (uncorrected)

| Read point | Raw classifier | Within style (rel / raw), p | rel − style (lower 95%) | Split runs, follower higher (rel / raw) | Overlap, test b |
|---|---|---|---|---|---|
| R1 T-start | 0.61 (p 0.04) | 0.09 / 0.07 | +0.08 (−0.09) | 6/9 · 5/9 | 0.58 |
| R1 T-end | 0.51 | 0.72 / 0.39 | −0.05 (−0.18) | 7/9 · 3/9 | 0.51 |
| R2 T-start | 0.64 (p 0.02) | 0.06 / 0.04 | +0.12 (−0.03) | 6/9 · 7/9 | 0.63 (p 0.06) |
| R2 T-end | 0.67 (p 0.005) | 0.11 / 0.005 | +0.06 (−0.08) | 7/9 · 4/9 | 0.45 |
| **R3 T-start** | **0.77 (p < 0.001)** | **0.001 / < 0.001** | **+0.23 (+0.06)** | 4/9 · 5/9 | 0.53 |
| R3 T-end | 0.62 (p 0.04) | 0.14 / 0.04 | +0.07 (−0.13) | 5/9 · 5/9 | 0.62 (p 0.09) |

- The style baseline alone is at chance (0.51), so instruction wording alone doesn't predict follow-through at this sample size.
- Run-level token overlap (joint-judge follow-up A) carries no follow-through signal at any read point.

## Checks (exploratory, after seeing the results)

- **The text baseline is biased below chance.** With labels shuffled 20 times, the held-out text classifier averages AUROC **0.34** and the lens classifier **0.47**. Leaving out whole scenarios pushes a classifier's held-out predictions against each fold's base rate, and the TF-IDF model, which learns scenario vocabulary, is hit hardest. The text baseline's 0.27–0.30 is therefore not a real anti-signal, and "lens − text" differences are not interpretable. The lens's own estimates are, if anything, slightly conservative.
- **The R3 T-start signal is mostly run-level.** The mean held-out lens score of a run's two colluders is **0.74** in runs where neither followed through (9 runs), **0.82** where one did (9) and **0.85** where both did (32). Within runs it doesn't separate the follower (4 of 9 split runs).
  - The round-3 prompt contains two rounds of public discussion. The lens may be reading where the discussion is going, and whether the colluder's side is winning, rather than a private decision.
  - Round 4's text judge reading the discussion reached similar separation at run level (test b 0.80; the joint discussion judge 0.75).

## What this means

- **The read position matters.** At the round-4 prompt end (P1, P2), lens tokens showed only who was instructed. At the start of the colluders' last discussion turn, they also predict, held out by scenario, whether the colluders will act on it. It's the first follow-through signal in the series that beats instruction wording.
- **We can't yet credit it to the lens rather than the discussion.** The signal is run-level and appears once two rounds of discussion are in the prompt. A judge reading the discussion gets similar run-level separation. A valid text baseline is needed before any "beyond text" claim.
- **It doesn't pick the individual** who follows through in split runs, so it is not yet evidence of a readable per-agent decision.

## Next steps

1. **A valid text baseline**, then a paired comparison at R3 T-start:
   - the *whole* public discussion up to round 3, not only the colluder's own messages;
   - a scoring that doesn't suffer the held-out-scenario bias (for example, a frozen judge rather than a trained classifier, or the round-4 discussion judge's scores).
2. **Replicate R3 T-start** with more data (next-steps §3: 2–3 more seeds per scenario), which also gives more split runs.
3. **Look at what the classifier uses** at R3 T-start: its top-weighted (layer, token) features, read with roles hidden first.

## Reproduce

```sh
uv run col lens-judge turns tokens --model <Qwen3-32B dir>   # reads the stored extraction; ~8 min
uv run col lens-judge turns analyse                          # CPU; ~4 min
```

- **Logs:** `results/logs/2026-10-24T23-22_turns-tokens.log` and `results/logs/2026-10-24T23-30_turns-analyse.log`.
- **Backup:** `/workspace/backups/discussion-turns-2026-10-24/`.
- **Provenance:** seed 0; Qwen/Qwen3-32B @ 9216db5; lens sha256 0af5ccf2…; NARCBench @ 85fea3b; repo `7a3538c`.
