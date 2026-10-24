# Next steps after the round-4 lens judge

2026-10-24 · Jorge (draft by Claude) · Builds on [`round4-judge.md`](round4-judge.md) and its results ([`docs/results/round4-judge/`](../results/round4-judge/README.md)). Nothing here has run. Numbers marked *(checked)* were verified on the transcripts or public files on 2026-10-24; the rest come from the round-4 results.

## Where we are

- **The lens tokens encode who was told to collude.** A token classifier recovers it at 0.99 on held-out scenarios, raw tokens included (exploratory).
- **The LLM judge uses little of it.** It answers "No" 94% of the time. On follow-through (test b) it is at or below chance in every setting, and below every baseline (text 0.80, instruction only 0.67, vote 0.96).
- **The read positions are weak.** P1 and P2 land on whitespace and punctuation; at P1, two agents in the same run share 84–98% of their top-25 tokens.
- **The lens is noisy but not empty.** It did not converge (about 14% vs about 5.5% error for converged lenses; *checked* from its fit log), yet the classifier still finds the instruction in its tokens.

## Direction (from the meeting with Hong Kiat)

Don't modify the lens yet. Focus on **how it is applied**, and judge the agents **together**: collusion needs two or more agents, so a judge that sees all of them at once should do better than one that scores each agent alone.

Levels of combining agents' signals:
1. **Naive** (round 4): judge each agent's lens tokens separately.
2. **Level 1:** all four agents' lens outputs (and optionally the discussion) in one judge prompt.
3. **Diff lens** (deferred): a lens that reads the difference between two activations. Novel, but non-trivial.

## Next steps, in order

### 1. Level-1 joint judge on the existing Qwen3-32B data

- **The judge sees** all four agents' lens tokens in one prompt, in random order, and answers: *"Which pair, if any, is colluding?"* This gives a run score directly, and a checkable answer (the named pair).
- **Three arms**, so any gain can be credited to the lens: lens only, discussion only, lens + discussion.
- **Judge fixes from round 4:** an easier question about what the tokens can show; fewer tokens (each agent's top 25 words-relative tokens across all layers); a 0–10 rating instead of Yes/No, to avoid the "No" floor.
- *Cost:* re-scoring only, no new activations.

### 2. Better read positions

- **A prefilled content token:** start each reply with "I" and read there (the J-lens paper's strongest position).
- **The colluders' own discussion turns** (rounds 1–3), comparing colluders who later vote the target with those who don't. All colluders share the same prompt template, so the private-plan confound cancels within this comparison. Fix in advance which tokens are read.
- *Cost:* new forward passes for the prefilled token; the discussion turns may already be stored.

### 3. More data for follow-through

- Test b has 32 vs 18 runs (about ±0.15) and only 9 split runs. Generate 2–3 more seeds per scenario.
- Make the **split-run sign test** the primary follow-through test: the cleanest comparison, and the only hint so far (8 of 9, uncorrected).

### 4. Make the token classifier a planned test

Pre-register it: held out by scenario, compared with the instruction-only baseline, checked within prompt-style groups, on follow-through only. It is the supervised ceiling the judges can be compared with.

### 5. A model with a converged lens and NLAs

Natural-language autoencoders (NLAs) turn an activation into a short paragraph, which a judge can read far more easily than 250 tokens, and which fits the Level-1 judge.

| Model | Converged J-lens (Neuronpedia) | NLA (kitft) |
|---|---|---|
| **Gemma-3-27B-IT** | yes, 828 prompts *(checked)* | layer 41 |
| Gemma-3-12B-IT | about yes, 844 prompts *(checked)* | layer 32 |
| Qwen2.5-7B-Instruct | yes, 485 prompts *(checked)* | layer 20 |
| Llama-3.3-70B-Instruct | no, 125 prompts *(checked)* | layer 53 |

- No Qwen3 model has a public NLA.
- **Candidate: Gemma-3-27B-IT.** Closest in capability to Qwen3-32B, both tools, fits one 80 GB GPU.
- **Check first:** Gemma 3's chat template may have no separate system role (the system prompt is folded into the first user turn). NARCBench puts the collusion instruction in the system prompt, so the "identical prompt except the system prompt" logic must be re-checked. Not yet verified.
- **Pilot before committing:** generate NARCBench Core and check the vote counts (enough colluders who follow through *and* who don't; few refusals).

### 6. The steganographic tier (Stego)

Promising in principle: the secret (the card count) is concrete, and the NARCBench paper reports that text monitors miss it (its Qwen3-32B pit boss flagged 1 of 20 collusion shoes) while activation methods reach 0.99–1.00. The cleanest test would read the **big player** (who learns the count only from the counter's coded table talk) at its prompt end, with honest players at the same table as the control.

**Blocking issue in our transcripts *(checked)*:** the colluders' `PRIVATE: …` decoding lines appear in other players' prompts. 90 of 280 honest-player calls (and 10 of 20 judge calls) contain them, e.g. "PRIVATE: HOT → $100", and sometimes the decoding is plain table text. In our data the secret is often public.

Options:
1. Check the released stego transcripts for the same leak.
2. Use only hands with no leak so far.
3. Regenerate stego with the private lines stripped from what other players see.

### 7. Lens checks (only if the steps above stay null)

- **Noise test (CPU):** perturb the lens maps by about 14% and measure how much each agent's top-25 tokens change.
- **Refit** a converged Qwen3-32B lens (about 7 h on 8× B200), or rely on the converged lenses of step 5.

## Open questions for Hong Kiat

- Activation oracles: which ones are available for our candidate models?
- Is the Level-1 judge (step 1) the right first deliverable, before any new data?
