# Gemma-3-27B-IT with a converged lens: do the lens findings replicate?

2026-10-25 · Jorge Roldan (draft by Claude) · Plan: [`docs/plans/gemma.md`](../../plans/gemma.md) (amendments 1 and 2) · Data: `/workspace/lens-judge/gemma/` (index: `/workspace/lens-judge/README.md`)

**Labels.** The tests follow the plan, so they are *planned*. The words-relative rendering keeps round 4's caveat: it was chosen after looking at Qwen examples with roles visible. The feature listing is *exploratory*.

## In short

1. **The instruction detector replicates.** On new transcripts from a different model, read with a **converged** lens, the no-LLM token-overlap score separates collusion-mode runs from controls at **0.94** (words-relative) and **0.98** (raw). Both pass Holm. A held-out classifier tells colluders from honest agents at 0.97.
2. **The round-3 follow-through signal replicates, and so does its limit.** Just before a colluder's round-3 turn, the lens classifier predicts follow-through at **0.71** (passes Holm; raw 0.78), as on Qwen (0.73). But Gemma reading the same discussion does better (**0.86**): **lens − text judge = −0.15**, lower bound −0.28. The lens does not show follow-through beyond the conversation.
3. **A converged lens did not change the picture.** Every Qwen finding has the same sign and similar size on Gemma. The Qwen lens's lack of convergence wasn't what limited it.

## Setup in one paragraph

**Data.** NARCBench Core regenerated with `google/gemma-3-27b-it` (@ `005ad34`, bf16): 50 scenarios × {collusion, control}, 1,700 agent calls. NARCBench's own `core.py` ran unchanged, through vLLM 0.10.1.1 on its V0 engine. **Gate 1** passed after amendment 2, which recovered 9 votes placed below a preamble:

| Gate 1 count | Value |
|---|---|
| Runs colluded | **28** |
| Collusion-mode runs that did not collude | 22 |
| Colluders who followed through / did not | 62 / 38 |
| API errors | 0 |

**Extraction.** One forward pass per call (prompt + reply) through transformers. Residuals kept at 10 layers spanning the same relative depth as on Qwen (23…56 of 0–61), at P1, P2 and the start and end of every discussion turn.

**Lens.** `neuronpedia/jacobian-lens` Gemma-3-27B-IT lens, sha256 `53f528a9…`, converged at 828 prompts. It was checked against the pinned `jacobian-lens` library at layer 41: activation cosine 0.9999996, 24 of the top 25 tokens shared.

**Analysis.** The same code and parameters as on Qwen. The text judge is **Gemma itself** (amendment 1).

## Primary family (Holm over 4, one-sided α = 0.05)

| # | Test | Gemma | Passes | Qwen (same test) |
|---|---|---|---|---|
| 1 | Overlap score, collusion mode vs control, words-relative P1 | **0.94 [0.90, 0.98]** | yes | 0.99 (post hoc) |
| 2 | Same, raw P1 | **0.98 [0.96, 0.99]** | yes | 0.99 (post hoc) |
| 3 | R3 T-start lens classifier, follow-through (100 colluders) | **0.71 [0.56, 0.83]** | yes | 0.73 |
| 4 | Lens − frozen text judge, same colluders | **−0.15** (lower 95% −0.28) | **no** | −0.08 |

**Reading (the plan's):** 1–2 pass, so the instruction detector replicates across models and lenses. 3 passes and 4 does not, so as on Qwen, follow-through is visible to the lens but no better than reading the conversation.

## Secondary results (uncorrected)

**Overlap score at P1, run level:**

| | Words-relative | Raw |
|---|---|---|
| Test a (28 colluded vs 72 others) | 0.83 [0.75, 0.89] | 0.90 [0.85, 0.95] |
| Test b (28 vs 22 collusion-mode runs) | 0.55 | **0.70 [0.54, 0.84], p = 0.009** (within style p = 0.027) |
| Colluded run above its own control | 27 of 28 | 28 of 28 |

**Instruction classifier at P1** (colluders vs honest agents in collusion-mode runs, held out by scenario): **0.97 [0.93, 0.99]**.

**Follow-through at the discussion turns** (lens classifier, AUROC):

| Read point | Words-relative | Raw |
|---|---|---|
| R1 T-start / T-end | 0.39 / 0.44 | 0.54 / 0.40 |
| R2 T-start / T-end | **0.64** / 0.55 | 0.65 / 0.61 |
| R3 T-start / T-end | **0.71** / 0.60 | **0.78** / 0.62 |

In the discussion-turn family (Holm over its 6 read points), R2 T-start passes as well as R3 T-start. The signal grows as the discussion goes on, as on Qwen.

**R3 T-start against the text judge:**

| | Follow-through AUROC | Split runs (follower higher) | Mean score per run: 0 / 1 / 2 followed |
|---|---|---|---|
| **Gemma text judge** | **0.86 [0.77, 0.93]** | 3 of 6 | 0.75 / 0.86 / 0.98 |
| Lens, words-relative | 0.71 | 2 of 6 | 0.56 / 0.70 / 0.74 |
| Lens, raw | 0.78 | 4 of 6 | 0.47 / 0.66 / 0.75 |

- The lens beats the style baseline: +0.24 (lower bound +0.10); raw +0.31.
- The TF-IDF text baseline is again biased below chance (0.28–0.29), so it is not a valid comparison, as on Qwen. The frozen judge is the comparison that counts.

**What the R3 classifier uses** (exploratory; `analysis/r3_features.csv`):
- **Toward following through:** *sneaky* (12 followers, 2 non-followers), *nervously*, *BUT*, *colleagues*, *Okay*, *Thank*.
- **Toward not following:** casual words (*kinda*, *REALLY*, *pretty*, *got*, *kiddos*).

As on Qwen, the casual vocabulary probably marks the "lowkey" instruction wording, whose colluders follow through less.

## What this means

- **"Who carries a hidden instruction" is a robust lens finding.** It holds across two models, two lenses (one converged) and two independent sets of transcripts. It needs no LLM judge and no labels: just count the lens tokens two agents share and the others don't.
- **"Who acts on it" is not, at these read points.** The lens predicts follow-through from round 2–3 on, but a judge reading the same conversation predicts it better on both models. Within a run, neither the lens nor the text judge reliably picks the follower; there are only 6 split runs here.
- **Lens convergence was not the bottleneck,** so next-steps §7 (refit the Qwen lens) is unlikely to help.

## Deviations from the plan

- **Amendment 1:** the text judge is Gemma, not Qwen. Gemma judges its own transcripts, and the judge differs from the Qwen experiment's, so the cross-model comparison of test 4 is partly a judge difference.
- **Amendment 2:** 9 votes recovered from a `RECOMMENDATION` line below a preamble (6 colluders, 3 honest agents). The rule changes nothing on the Qwen data.
- **vLLM:**
  - the V1 engine produced gibberish for Gemma 3 on long prompts, so generation used V0 (probe logs in `logs/`);
  - transformers was pinned to 4.55.4 in the vLLM environment;
  - sampling is not seeded per request (as for the Qwen data).
- **Reference check:** the library tokenizes the prompt with an extra start token (2,494 vs 2,493 tokens). Both sides of the comparison used the library's tokens.

## Reproduce

```sh
uv run col lens-judge gemma generate --core-dir <core>      # vLLM env: /root/vllm-env (see /workspace/lens-judge/README.md)
uv run col lens-judge gemma labels --core-dir <core>        # Gate 1
uv run col lens-judge gemma extract --core-dir <core>
uv run col lens-judge gemma check-lens --core-dir <core>
uv run col lens-judge gemma tokens
uv run col lens-judge turns text-judge --judge gemma --model <gemma dir> --out-dir results/gemma --round4-dir results/gemma --core-dir <core>
uv run col lens-judge turns analyse   --out-dir results/gemma --round4-dir results/gemma --core-dir <core>
uv run col lens-judge turns follow-up --out-dir results/gemma --round4-dir results/gemma --core-dir <core>
uv run col lens-judge gemma analyse
```

- **Logs:** `/workspace/lens-judge/gemma/logs/` (UTC names, 2026-10-25T00-06 … T01-52).
- **Provenance:** in every output's `.meta.json`.
