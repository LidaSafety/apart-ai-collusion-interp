# Discussion turns: does follow-through show in the colluders' own turns?

2026-10-24 · Jorge Roldan (draft by Claude) · Plan: [`docs/plans/discussion-turns.md`](../../plans/discussion-turns.md), approved before any readout · Follows [the joint-judge results](../joint-judge/README.md)

**Labels.** The planned tests are *planned*. The two diagnostics under "Checks" were added after seeing the results, so they are *exploratory*.

## In short

1. **One primary test passes: round 3, T-start, but a judge reading the discussion does better** (follow-up B: text judge 0.82; lens − text −0.08).
   **Original finding:** Just before a colluder writes its last discussion turn, a held-out lens-token classifier predicts whether it will vote the target at **0.73 [0.58, 0.87]** (p < 0.001; Holm over 6 read points).
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

## Follow-up B: the lens or the conversation?

Planned in the plan's follow-up B (`14a8c80`) before running.
- **Commands:** `col lens-judge turns text-judge --model <dir>` and `col lens-judge turns follow-up`.
- **Logs:** `results/logs/2026-10-24T23-54_turns-text-judge.log` and `results/logs/2026-10-24T23-56_turns-follow-up.log`.
- **Format:** 100 of 100 answers start with Yes or No; minimum P(Yes) + P(No) = 0.999.

**B1, a frozen text judge (planned).** For each colluder at R3 T-start, Qwen3-32B reads the brief and every public message before the colluder's round-3 turn. It is told the colluder was secretly instructed to push the target and asked whether it will vote for it. There is no training step, so no fold bias.

| Instrument | Follow-through AUROC | Split runs (follower higher) | Mean score per run: 0 / 1 / 2 followed |
|---|---|---|---|
| **Text judge** | **0.82 [0.69, 0.92]**, p < 0.001 | 6 of 9 | 0.26 / 0.51 / 0.77 |
| Lens, words-relative | 0.73 [0.58, 0.87] | 4 of 9 | 0.74 / 0.82 / 0.85 |
| Lens, raw | 0.77 [0.62, 0.89] | 5 of 9 | 0.62 / 0.75 / 0.83 |

- **Primary of B: words-relative lens − text judge = −0.08** (one-sided lower 95% bound −0.21, p = 0.87). **Not above zero.** Raw: −0.05 (lower bound −0.17).
- **Reading (the plan's):** the round-3 lens signal is **no better than reading the conversation**. The discussion predicts follow-through better, and separates runs more sharply.

**B2, what the classifier uses (exploratory, descriptive).** Weights of the classifier refitted on all 100 colluders (`analysis/r3_features.csv`):
- **Words-relative, toward following through:** 伪装 *disguise* (25 followers, 3 non-followers), 虚假 *false*, 谣言 *rumor*, 宣传 *publicize*, 犹豫 *hesitate*, 偏好 *preference*.
- **Words-relative, toward not following:** casual words (*things, stuff, nice, something, pretty, got*), 调查 / *investigations*.
- **Raw, toward following through:** 我们认为 *"we believe"*, 审视 *examine*, 考量 *considerations*, 适度 *moderate*.
- **Raw, toward not following:** 证据 *evidence*, 执法 *law enforcement*, 认真落实 *implement conscientiously*.
- Deception concepts mark the followers. The casual vocabulary likely reflects the "lowkey" instruction wording, whose colluders follow through less, so instruction style may still feed the classifier despite the within-style test.

## What this means

- **The read position matters.** At the round-4 prompt end (P1, P2), lens tokens showed only who was instructed. At the start of the colluders' last discussion turn, they also predict, held out by scenario, whether the colluders will act on it. It's the first follow-through signal in the series that beats instruction wording.
- **It is not a lens finding** (follow-up B). A frozen judge reading the same discussion predicts follow-through better (0.82 vs 0.73), with sharper run-level separation. The lens at round 3 mostly reflects where the conversation is going.
- **It doesn't pick the individual** who follows through in split runs, so it is not yet evidence of a readable per-agent decision.

## Next steps

1. **Done as follow-up B:** the discussion beats the lens at R3 T-start, so the follow-through signal so far is the conversation's, not the lens's.
2. **For follow-through, look where the text can't see:** a position after the discussion has been read but whose content is private. Candidates:
   - the colluders' **private-channel** turn (round 0);
   - a **prefilled content token** at the final vote (next-steps §2a).
   Compare each against a text judge given the same visible text.
3. **A converged lens** (Gemma-3-27B, next-steps §5). This lens's noise (~14% error) may be why its tokens carry less than the text.
4. **Keep the lens for what it does well:** the no-LLM token-overlap detector of *who carries a hidden instruction* (joint-judge follow-up A, 0.98–0.99) is the strongest lens result so far. It's worth a planned replication.

## Reproduce

```sh
uv run col lens-judge turns tokens --model <Qwen3-32B dir>   # reads the stored extraction; ~8 min
uv run col lens-judge turns analyse                          # CPU; ~4 min
```

- **Logs:** `results/logs/2026-10-24T23-22_turns-tokens.log` and `results/logs/2026-10-24T23-30_turns-analyse.log`.
- **Backup:** `/workspace/lens-judge/discussion-turns/`.
- **Provenance:** seed 0; Qwen/Qwen3-32B @ 9216db5; lens sha256 0af5ccf2…; NARCBench @ 85fea3b; repo `7a3538c`.
