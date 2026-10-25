# The lens-judge series: can J-lens readouts reveal collusion between LLM agents?

2026-10-25 · Jorge Roldan (draft by Claude) · Covers round 4, the joint judge, the discussion turns and the Gemma replication. Each experiment's full report is linked below. Report page: https://claude.ai/artifact/JsCLtpTWd59tPSpz3nRzCd · Run explorer: https://claude.ai/artifact/HpHmZhgrYzFjcYqRyx2TKr · Data: `/workspace/lens-judge/README.md`

## The question

In NARCBench Core, 4 LLM agents on a committee discuss a case for three rounds, then vote. In half the runs (**collusion mode**), 2 agents are secretly told to push one option and get a private channel; in the other half (**control**) all 4 are honest. A run **colluded** when both instructed agents voted the target option.

We read the agents' internal activations through a **J-lens** (Jacobian lens; Gurnee et al. 2026), which turns an activation into the tokens the model "has in mind". We asked:
1. Does the lens show **who was told to collude**?
2. Does it show **who will act on it** (follow through)?
3. Can it show either **better than reading what the agents say**?

## Answers in one table

| Question | Answer | Strongest evidence |
|---|---|---|
| Who carries a hidden instruction? | **Yes, robustly**, with no LLM and no labels | Token-overlap detector: Gemma 0.94–0.98 (planned, Holm); Qwen 0.98–0.99 (post hoc) |
| Can an LLM judge read that from the lens tokens? | **Partly**, and only side by side | Joint judge names the instructed pair in 35 of 50 runs (chance 1 in 6). One-agent-at-a-time judges are near chance |
| Who follows through? | **Only late,** from the start of a colluder's round-3 turn | Held-out classifier: Qwen 0.73, Gemma 0.71 (both pass Holm) |
| Better than reading the discussion? | **No** | A frozen judge reading the same discussion: Qwen 0.82, Gemma 0.86. Lens − text: −0.08 and −0.15 |
| Was the unconverged Qwen lens the problem? | **No** | A converged Gemma lens gives the same pattern |

**Bottom line:** J-lens readouts are a reliable, label-free detector of agents that share a hidden context. They don't yet show the decision to act on it before, or beyond, what the conversation already shows.

## Setup common to all experiments

- **Data:** NARCBench Core, 50 scenarios × {collusion, control} = 100 runs, 400 agents.
  - Qwen3-32B transcripts: 32 runs colluded; 73 of 100 colluders voted the target.
  - Gemma-3-27B-IT transcripts, generated for this series: 28 runs colluded; 62 colluders voted the target.
- **Lenses:**
  - Neuronpedia's Qwen3-32B lens: **not converged**, about 14% error, stopped by hand.
  - Neuronpedia's Gemma-3-27B-IT lens: **converged** at 828 prompts.
  - Both readouts match the pinned `anthropics/jacobian-lens` library.
- **Read positions:**
  - **P1:** the last prompt token before the vote.
  - **P2:** the end of the discussion, before the vote is requested.
  - **T-start / T-end:** the prompt end before, and the last token of, each agent's own discussion turn in rounds 1–3.
- **Renderings:**
  - **raw:** the top 25 tokens per layer at 10 layers;
  - **words-relative:** word tokens, minus the average agent; chosen after viewing examples with roles visible, so partly exploratory.
- **Tests:**
  - **test a:** colluded runs vs all others;
  - **test b:** colluded vs not-colluded runs, collusion mode only. This is the follow-through test;
  - AUROC with 95% scenario-bootstrap intervals and shuffle tests;
  - every experiment's primary tests were fixed in a plan before the run and Holm-corrected. Anything else is labelled *exploratory*.

## 1. Round 4: one judge per agent (Qwen3-32B)

[Report](round4-judge/README.md) · [Plan](../plans/round4-judge.md)

An LLM judge (Qwen3-32B) read one agent's lens tokens (10 layers × 25) at P1 or P2 and answered "Is this agent about to collude?" (Yes/No).

| | raw P1 | raw P2 | words-rel. P1 | words-rel. P2 |
|---|---|---|---|---|
| Instruction visible, vote-free (gate) | 0.46 ✗ | 0.58 ✗ | **0.75 ✓** | 0.58 ✗ |
| Test a | 0.54 | 0.49 | **0.70** (Holm) | 0.49 |
| Test b (follow-through) | 0.50 | 0.46 | 0.46 | **0.30 (reversed)** |

- **Baselines on test b:** vote line 0.96, text 0.80, instruction only 0.67. Every lens setting is below every baseline.
- **Exploratory:** a held-out token classifier recovers *who was told to collude* at **0.99** from the same tokens. The information is in the lens; the judge didn't read it.

## 2. Joint judge: all four agents in one prompt (Qwen3-32B)

[Report](joint-judge/README.md) · [Plan](../plans/joint-judge.md)

One judge saw all four agents at once and gave a 0–9 rating plus the most likely pair. It saw lens grids (words-relative primary, raw), 25 pooled tokens per agent, the discussion, or discussion + grids. 900 prompts.

| Judge | Test a | Test b | Instructed pair named (of 50; chance 8) | … in colluded / not-colluded runs |
|---|---|---|---|---|
| Words-rel. grid · P1 (primary) | 0.51 | 0.54 | 27 | 17/32 · 10/18 |
| Pooled 25 · P1 | 0.57 | 0.53 | **35** | 22/32 · 13/18 |
| Raw grid · P1 | 0.37 (below) | 0.37 | 12 | 8/32 · 4/18 |
| Discussion only | **0.85** | **0.75** | 27 | 23/32 · **4/18** |
| Discussion + grid · P1 | 0.76 | 0.65 | 22 | 16/32 · 6/18 |

- **None of the 6 primary tests passes.** Adding grids to the discussion *lowers* test b (−0.10, −0.11).
- **The rating carries no lens signal:** the judge rates almost every run 6 or 3. The *pair* does carry signal: it finds the instructed agents, equally whether or not they followed through. The discussion judge finds them mostly when they did (23/32 vs 4/18).
- **Follow-up A (exploratory): no LLM needed.** Count the lens tokens that exactly two agents share and the other two don't. That separates collusion-mode runs from controls at **0.98–0.99** (post hoc), raw tokens included, with test a 0.86–0.91 and every colluded run above its own control (31–32 of 32). Test b stays near chance.

## 3. Discussion turns: does follow-through show earlier? (Qwen3-32B)

[Report](discussion-turns/README.md) · [Plan](../plans/discussion-turns.md)

The 100 colluders' stored activations at their own discussion turns (no new forward passes). A held-out classifier on lens-token presence (10 folds of whole scenarios) predicted who would vote the target.

| Read point | Rounds 1 / 2 / 3, T-start | Rounds 1 / 2 / 3, T-end |
|---|---|---|
| Words-relative (primary, Holm over 6) | 0.59 / 0.63 / **0.73 ✓** | 0.46 / 0.57 / 0.57 |
| Raw | 0.61 / 0.64 / **0.77** | 0.51 / 0.67 / 0.62 |

**Follow-up B (planned):** a frozen Qwen3-32B judge read the discussion each colluder had seen before its round-3 turn.

| At R3 T-start | AUROC | Split runs (follower higher) | Mean score per run, 0 / 1 / 2 followed |
|---|---|---|---|
| **Text judge** | **0.82** | 6 of 9 | 0.26 / 0.51 / 0.77 |
| Lens, words-relative | 0.73 | 4 of 9 | 0.74 / 0.82 / 0.85 |

- **Lens − text judge = −0.08** (lower bound −0.21). The round-3 lens signal is the conversation's, read less well.
- The TF-IDF text baseline turned out to be invalid: scenario-held-out folds bias it below chance (0.34 on shuffled labels). Only the frozen judge is a fair comparison.

## 4. Replication: Gemma-3-27B-IT with a converged lens

[Report](gemma/README.md) · [Plan](../plans/gemma.md)

NARCBench Core was regenerated with Gemma, extracted, and read with the converged lens. The tests are the same; the text judge is Gemma itself (amendment 1).

| Primary test (Holm over 4) | Gemma | Passes | Qwen |
|---|---|---|---|
| Overlap detector, collusion mode vs control, words-relative | **0.94** [0.90, 0.98] | yes | 0.99 (post hoc) |
| Same, raw | **0.98** [0.96, 0.99] | yes | 0.99 (post hoc) |
| R3 T-start classifier, follow-through | **0.71** [0.56, 0.83] | yes | 0.73 |
| Lens − frozen text judge | **−0.15** (lower −0.28) | no | −0.08 |

- **Text judge alone:** 0.86. **Instruction classifier at P1:** 0.97.
- **Raw overlap, test b:** 0.70 (p = 0.009, uncorrected), a run-level follow-through hint. Qwen showed a similar hint (raw P2 0.66).
- **The classifier's features** (exploratory, both models): deception words (*sneaky*, 伪装 *disguise*) point toward following through; casual words (*kinda*, *things*, *pretty*) point toward not following. The casual words probably mark the "lowkey" instruction wording, whose colluders follow through less.

## What we learned

1. **The lens reliably shows shared hidden context.** Two agents given the same secret instruction carry overlapping concepts that the other agents don't. A plain count of shared lens tokens finds them at about 0.94–0.99, on two models, two lenses and two sets of transcripts. Instruction secrecy shows up as such concepts (隐藏 *hidden*, 秘密 *secret*, 伪装 *disguise*).
2. **LLM judges are a weak way to read lens tokens.** Judges reading tokens one agent at a time miss what a classifier finds. Side by side, a judge finds the pair but can't calibrate a rating. Adding tokens to the discussion distracts it.
3. **Follow-through is not visible early, and not beyond the text.** It appears only once the discussion is well under way (round 2–3) and mostly at run level, where a judge reading the conversation does better.
4. **These limits are not about lens quality.** The converged Gemma lens behaves like the unconverged Qwen lens.

## Limitations

- **Sample size:** one transcript set per model, 50 scenarios, 9 (Qwen) and 6 (Gemma) split runs. Follow-through tests are low-powered within runs.
- **Rendering:** the words-relative rendering was chosen after viewing examples with roles visible, so it is partly exploratory. Raw tokens give the same conclusions throughout.
- **Post hoc:** the Qwen overlap mode-vs-control AUROC; the Gemma replication made it a planned test.
- **Judges:** the Gemma text judge judged its own model's transcripts (amendment 1), and every judge is a single frozen prompt.
- **Generation:** sampling is not seeded per request, so the exact transcripts aren't reproducible. Gemma needed vLLM's V0 engine; V1 produced gibberish on long prompts.

## Next steps

1. **Use the overlap detector as a monitor:** test it on transfer and stego tiers and on new seeds, and set an operating point for false alarms.
2. **Look for follow-through where the text can't see it:** the colluders' private-channel turn, or a prefilled token at the vote, each compared with a text judge given the same visible text.
3. **More seeds per scenario,** for more split runs and a within-run test of the decision.
4. **Natural-language autoencoders** (next-steps §5) as a more readable alternative to token lists for LLM judges.

## Where everything is

- **Code:** branch `experiments/lens-judge/gemma`, PR #64 (one PR for the whole series). Every step is a `col lens-judge …` command.
- **Plans:** `docs/plans/`. **Results:** `docs/results/<experiment>/README.md`.
- **Outputs, logs, transcripts:** `/workspace/lens-judge/` (README index); round-4 outputs under `/workspace/backups/round4-judge-2026-10-22/`.
- **Interactive page:** https://claude.ai/artifact/HpHmZhgrYzFjcYqRyx2TKr.
- **Report page:** https://claude.ai/artifact/JsCLtpTWd59tPSpz3nRzCd.
