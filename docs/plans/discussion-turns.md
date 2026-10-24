# Plan: do the colluders' own discussion turns show who will follow through?

2026-10-24 · Jorge (draft by Claude) · Next-steps §2 ([`next-steps.md`](next-steps.md)), after the [joint-judge results](../results/joint-judge/README.md). **Draft, for approval. Nothing has run.**

## Why

Every lens readout so far, at the round-4 prompt end (P1) and the end of the discussion (P2), shows *who was told to collude* (unsupervised token overlap 0.98–0.99; supervised classifier 0.99) but not *who acts on it*:
- the round-4 classifier reached 0.63–0.83 on follow-through;
- every judge's test b is near chance.

The decision may form earlier, while each colluder writes its discussion turns.

## Question

Among the 100 colluders (73 voted the target, 27 did not), do the lens tokens at their own discussion turns in rounds 1–3 predict who will vote the target? And at run level, do the 32 collusion-mode runs that colluded differ from the 18 that did not?

## Data (all stored; no new forward passes)

- `/workspace/extract/ours-qwen3_32b/qwen3_32b/core/`: all 1,700 calls, named positions × 64 blocks. The 1,200 discussion calls (400 agents × rounds 1–3) are all present.
- **Read points:** 3 rounds × 2 positions = **6**.
  - **T-start** (`response_start`): the last prompt token before the agent writes its turn, like P1.
  - **T-end** (`resp_last`): the last token of the agent's own message, after it has argued.
- **Why the private-plan confound cancels:** every colluder's prompt holds the private messages and an instruction from one template (standard or lowkey). So comparing colluders who follow through with those who don't removes *instruction presence*. Instruction *wording* (style) remains, and is controlled by within-style tests and a style baseline.
- **Lens and readout:** as round 4.
  - Same lens and the same 10 layers (24…58).
  - **Words-relative** (log-probabilities minus the mean over all 1,200 discussion calls at that round, position and layer; word tokens only; top 25) and **raw** (top 25 printable).

## Instruments

1. **Token classifier (supervised; primary).** Round 4's exploratory classifier, now planned:
   - **features:** token presence (layer, token) in the top 25;
   - **model:** logistic regression, C = 0.1, not tuned;
   - **evaluation:** 10 folds held out by scenario, seed 0;
   - **label:** voted the target, among the 100 colluders;
   - run at each of the 6 read points, words-relative.
2. **Baselines, same classifier and folds:**
   - **style:** the colluder's instruction style, the run's style group and the round;
   - **text:** TF-IDF of the colluder's own public messages up to and including that turn.
3. **Token overlap at run level (unsupervised; from joint-judge follow-up A):** the largest pair's exclusive (layer, token) overlap minus the median over the 6 pairs, among the 4 agents of a run at the same read point. Test b compares 32 colluded runs with 18 that did not collude.

## Tests

| Test | Units | Method |
|---|---|---|
| **Classifier follow-through**, words-relative, 6 read points | 100 colluders (73 vs 27) | held-out AUROC, 95% scenario bootstrap (10,000), plain shuffle (10,000) |
| Classifier − style baseline, − text baseline | same | one-sided paired scenario bootstrap |
| Classifier within style | same | shuffle within instruction style |
| Split runs | 9 runs, one colluder followed and one didn't | sign test on held-out classifier scores |
| Raw-rendering classifier | same | as above |
| Overlap test b, 6 read points | 50 collusion-mode runs | AUROC, bootstrap, shuffle |

- **Primary family:** classifier follow-through, words-relative, at the 6 read points. Holm, one-sided α = 0.05. Everything else is secondary and uncorrected.
- **Reading:**
  - above chance *and* beats the style baseline → the discussion-turn activations carry follow-through beyond instruction wording;
  - beats the text baseline too → the lens shows it before or beyond what the agent writes.

## Not in this plan

- **The prefilled "I" token** (next-steps §2a) needs new forward passes. It is deferred until this cheaper, stored-data test is in.
- **An LLM judge on these tokens.** Both judges so far read much less than a classifier, so it is used only if the classifier finds a signal.

## Outputs and commands

`results/discussion-turns/` (gitignored), with provenance. Commands under `col lens-judge turns …`:
- `tokens` (GPU, or CPU at about 10× slower): read the stored activations, compute both renderings;
- `analyse` (CPU): the tests above.

## Cost

- Reading 24 GB of shards from `/workspace` (about 15–25 min, slow FUSE disk).
- Lens readouts for 1,200 calls × 2 positions × 10 layers (minutes on the GPU).
- Classifiers and bootstraps on the CPU (about 10 min).
- About 1 hour in all.
