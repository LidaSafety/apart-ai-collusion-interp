# Plan: replicate the lens findings on Gemma-3-27B-IT, with a converged lens

2026-10-25 · Jorge (draft by Claude) · Next-steps §5 ([`next-steps.md`](next-steps.md)). Requested by Jorge ("use Gemma-3-27B"). Written before any generation, extraction or readout.

## Why

On Qwen3-32B (lens **not converged**, ~14% error), the lens:
- shows **who carries a hidden instruction**: a no-LLM token-overlap detector separates collusion-mode runs from controls at 0.98–0.99 (post hoc);
- shows **follow-through** only at the colluders' round-3 turn (0.73), where a judge reading the discussion does better (0.82).

Question: with a **converged** lens on a different model, do those findings replicate, and does the lens now show follow-through beyond the text?

## Model, lens, checks already done (2026-10-25)

- **Model:** `google/gemma-3-27b-it` @ `005ad3404e59d6023443cb575daa05336842228a`, bf16, 62 layers, d = 5376 (54.9 GB). Access works.
- **Lens:** `neuronpedia/jacobian-lens` @ `e166deb`, `gemma-3-27b-it/jlens/Salesforce-wikitext/gemma-3-27b-it_jacobian_lens.pt`, sha256 `53f528a9…09d9` (3.5 GB).
  - **Converged:** the fit stopped by its own rule at 828 prompts (mean relative change 0.0019 < 0.002).
  - The Qwen lens was stopped by hand.
- **Chat template:** Gemma 3 has no system role; the template puts the system text at the start of the first user turn, followed by a blank line.
  - Every NARCBench call is one system + user pair, so agents still differ only in that leading text, and the round-4 "same prompt except the instruction" logic holds.
  - What may change is behaviour: Gemma reads the collusion instruction as user text. Gate 1 checks this.

## Steps

1. **Setup (label-free):**
   - free `/dev/shm` (remove the Qwen weights; re-downloadable in ~5 min);
   - download Gemma and the lens, and check the lens sha256;
   - install vLLM in a separate uv environment outside the repo, with its version pinned and recorded.
2. **Generate NARCBench Core with Gemma:**
   - run `third_party/narcbench/generation/core.py` **unchanged**: 50 scenarios × {collusion, control}, NARCBench's defaults (temperature 0.7, max 512 tokens, its per-scenario seeds);
   - served by vLLM with `google/gemma-3-27b-it` at the pinned revision;
   - output in `data/raw/gemma_3_27b/core` (on `/workspace`).
3. **Gate 1, decided before looking at anything else.** Continue only if all hold:
   - every final vote parses;
   - at least 15 runs colluded (both colluders voted the target);
   - at least 10 collusion-mode runs did not collude;
   - at least 15 colluders did not vote the target.

   Otherwise stop and report. NARCBench's labels then follow the round-4 definition (code: `col lens-judge labels`, adapted to the model folder).
4. **Extract residuals** (new code in `colx`, Gemma-aware): one forward pass per agent call over prompt + reply, using the chat template as rendered for generation. Kept at the read points and layers below. bf16, stored on `/workspace`.
5. **Lens readouts:** raw and words-relative top 25 per layer, the same rules as on Qwen. The readout must match the pinned `anthropics/jacobian-lens` library at one layer, as on Qwen.
6. **Tests below**, with the same code and parameters as on Qwen.

**Read points:**
- **P1:** the final call's last prompt token.
- **R3 T-start:** each colluder's round-3 discussion prompt end.
- **P2** (end of discussion), and T-start/T-end at rounds 1–3: secondary.

**Layers:** 10 evenly spaced over the same workspace band, 38–92% of depth: **23, 27, 30, 34, 38, 41, 45, 49, 52, 56** (of 0–61). *Why:* the same relative depths as Qwen's 24…58 of 63.

## Tests

| # | Test | Units | Method |
|---|---|---|---|
| **1** | **Overlap detector, collusion mode vs control** (words-relative, P1) | 100 runs | AUROC, scenario bootstrap (10,000), shuffle within scenario (10,000) |
| **2** | Same, **raw** tokens, P1 | 100 runs | same |
| **3** | **R3 T-start lens classifier, follow-through** (words-relative) | colluders | held-out by scenario, as on Qwen |
| **4** | **R3 T-start lens − frozen text judge** (words-relative) | colluders | one-sided paired scenario bootstrap; the text judge as in follow-up B (Qwen3-32B as judge, to hold the judge fixed) |

- **Primary family:** tests 1–4, Holm, one-sided α = 0.05.
- **Secondary:**
  - overlap test a and test b, pair found;
  - the classifier at all 6 discussion read points, raw versions, split runs;
  - instruction-presence classifier at P1 (round 4's exploratory 0.99, now planned).

**Reading:**
- 1–2 pass → the instruction detector replicates across models and lenses.
- 3 passes but not 4 → as on Qwen: follow-through is visible, but no better than the text.
- **4 passes → with a converged lens, the lens shows follow-through beyond what the discussion says**, the result the series has been looking for.

## Not in this plan

- The joint LLM judge (2 hours of GPU for a null on Qwen).
- NLAs (next-steps §5): considered after this, if the lens tokens carry signal.

## Cost

| Step | Time |
|---|---|
| Setup | ~30 min |
| Generation | ~30–60 min, 1,700 calls |
| Extraction | ~30 min |
| Readouts | ~10 min |
| Text judge (Qwen re-download and scoring) | ~15 min |
| Analysis | ~10 min |
| **Total** | **about 3 hours** |

## Amendment 1 (2026-10-25, during generation, before any extraction or scoring)

By Jorge ("I want to judge with gemma first"):
- **Test 4's text judge is Gemma-3-27B-IT** (the same model that generated the transcripts). It uses the same prompt, question and score B as follow-up B on Qwen. Gemma is rendered with its own chat template; the prompt is one user turn.
- **Qwen3-32B as the judge is a later, secondary check.** It holds the judge fixed across the two models.
- **Caveat:** test 4 now compares the lens with a judge that differs from the Qwen experiment's, and that judges its own model's transcripts. A cross-model difference in "lens − text" is then partly a judge difference.
