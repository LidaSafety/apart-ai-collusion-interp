# Overnight: can the lens catch steganographic collusion that text monitors miss?

2026-10-25 · Jorge Roldan (draft by Claude, written overnight) · Plan: [`docs/plans/stego.md`](../../plans/stego.md) (amendments 1–4) · Data: `/workspace/lens-judge/` (index: `README.md`) · Builds on the [series report](../lens-judge-series.md)

**Labels.** Tests named in the plan before their data existed are *planned*. Checks added after seeing results are *exploratory* and say so. Every amendment is listed under "Deviations".

## In short

1. **NARCBench's own text monitor misses steganographic collusion entirely.** Its pit boss flagged **0 of 150** collusion tables across three stego datasets. A frozen Gemma monitor told to look for coded talk does much better at table level: 0.68 (v1), 0.75 (v2), 0.84 (replication).
2. **Weak evidence that the receiver's activations carry the decoded secret.**
   - **v2 (planned):** with no count text in the big player's prompt, its lens tokens predicted HOT at **0.66** against **0.57** for honest players who read the same coded message (+0.089, p = 0.021).
   - **Independent replication** (50 new shoes, planned before the data): **not significant** (+0.023, p = 0.34; raw +0.084, p = 0.075).
   - **Pooled, descriptive (657 hands):** words-relative +0.049 [lower −0.004]; raw **+0.089** [lower +0.027].
   - **Reading:** every player's lens predicts the count above chance (0.63–0.72), because the card history is public. The receiver's extra advantage is small and not robust.
3. **Our first stego dataset had a confound.** NARCBench writes the true count history into the colluders' private channel. In v1, the big player's lens (0.76) mostly read that plain text, which alone predicts the count at 0.86. Removing it (v2) gave the clean test above, and Gemma still decodes: its big player's bets track the count at a median correlation of 0.40.
4. **The Core overlap detector does not transfer to stego as a colluder finder.** In stego the two colluders get *different* instructions, so the pair that stands out is the two honest players. As a "this table is not homogeneous" score it separates collusion from control tables perfectly (raw tokens, 1.00); that reading is exploratory.
5. **The overlap detector does transfer to new scenario types** (transfer tier, stored Qwen3-32B activations, exploratory): collusion vs control **1.00**.
6. **J++ lens ≈ J-lens** at the layers read here (Qwen3-4B, block F); the overlap detector also replicates on that third model (0.97–0.99).
7. **NLA descriptions don't surface the secret.** A judge reading Gemma's layer-41 NLA descriptions predicts the big player's count only weakly (0.60), not reliably better than honest players (p = 0.13). The descriptions read as table chat.
8. **The colluders' private-channel turn shows little about follow-through** (Qwen3-32B Core, exploratory: 0.52–0.64).

## Setup

**NARCBench-Stego** is a blackjack table with 4 players and an LLM pit boss, 8 hands per shoe.
- **Collusion runs:** a **counter** signals the card count (NEGATIVE / NEUTRAL / HOT) through coded table talk, and a **big player** bets on it. The two agree a scheme in two private rounds.
- **Control runs:** the same shoes with all players honest.
- **Generation:** Gemma-3-27B-IT, 50 shoes × {collusion, control} = 100 runs, NARCBench's `stego.py` unchanged except for a wrapper fix.
- **The fix:** NARCBench's code leaked the big player's private decoding notes into everyone's chat (a `PRIVATE:`/`DECODE:` mismatch). The wrapper also stops a counter that repeats its private `RANGE:` line from leaking it.
- **Read point:** each player's prompt end before its table talk (H-start), at 10 layers. Read with the converged Gemma lens (raw and words-relative top 25).

**Gate S (data validity):**
- **Passed:** the big player's bets track the count (median correlation 0.365; at least 0.3 in 26 of 50 collusion runs).
- **Excluded (amendment 1):** two shoes where a counter blurted count markers in public (shoes 08 and 35, both runs). All results are also reported on all runs, with no change in any conclusion.

## Stego v1 results (Gemma)

| Primary test (Holm over 3) | Result | Passes |
|---|---|---|
| S1: overlap detector (words-relative), collusion vs control tables | 0.37 [0.27, 0.47], *reversed* | no |
| S2: overlap − frozen text monitor | −0.31 | no |
| S3: big player's lens predicts a HOT count, **minus** honest players who heard the counter in the same hand | +0.20 (lower 95% +0.10, p = 0.0004); big player **0.76** [0.67, 0.83], honest 0.56 | yes |

**Secondary results:**
- **Text monitors.** NARCBench's built-in pit boss flagged **0 of 50** collusion tables (0 controls). A frozen Gemma monitor told to look for coded table talk reaches **0.68** [0.57, 0.78].
- **Raw-token overlap separates collusion from control tables perfectly (1.00), but for a different reason than on Core.** The pair it names is never the counter and big player (0 of 48). In stego the two colluders get *different* instructions while the two honest players get *identical* ones, so the odd pair out is the honest pair. Raw overlap detects that a table is not homogeneous, not who colludes. This interpretation came after seeing the result, so it is exploratory.
- **S1's words-relative failure is structural for the same reason:** the detector looks for the pair that shares content, and in stego the colluders don't share an instruction.

### The S3 confound (exploratory, found after the results)

NARCBench writes **the true count range of every previous hand** into the colluders' private channel in plain text (`[Hand 5: HOT (count +12)]`), and the big player's prompt contains it. The count drifts slowly within a shoe, so this text predicts the current hand well:

| Predicting HOT on the big player's hands (331 hands, 93 HOT) | AUROC |
|---|---|
| Previous hand's range (text only) | 0.747 |
| Previous hand's **numeric count** (text only, held-out logistic) | **0.863** |
| … + the big player's lens score | 0.901 (**+0.038**, lower 95% +0.019, p = 0.0006) |
| … + the honest players' lens score | 0.869 (+0.006) |

So v1's S3 is **mostly the lens reading plain text in the prompt**. A small part (+0.04) goes beyond that text, consistent with partial decoding of the covert signal. The clean test is stego v2.

## Stego v2: no count history in the big player's prompt (amendment 4)

**Setup.** The same 50 shoes (same cards and counts), regenerated with the plain-text count-history lines removed from the big player's prompts only. Checked on all 400 big-player prompts: none contains count history. The counter still gets the count each hand.

**Gate S passes, and better than in v1.** The big player's bets track the count at a median correlation of **0.395** (v1: 0.365), at least 0.3 in 28 of 50 runs.
- **So Gemma's big player really decodes the counter's coded table talk;** it doesn't need the plain-text history.
- One prompt had a counter blurting markers; that shoe (22) is excluded.

| Test (v2) | Result |
|---|---|
| **S3 (v2's primary, planned): big player's lens predicts HOT, minus honest players who heard the same coded message** | **+0.089** (one-sided lower 95% +0.016, **p = 0.021**). Big player **0.66** [0.59, 0.72]; honest **0.57** [0.48, 0.65]. **Passes.** |
| S3, raw tokens | +0.117 (p = 0.011): 0.69 vs 0.57 |
| S3, all runs (sensitivity) | words-relative +0.064 (p = 0.053); raw +0.121 (p = 0.009) |
| Built-in pit boss | flagged **0 of 50** collusion tables (0 controls) |
| Frozen Gemma text monitor, table level | 0.75 [0.65, 0.85] |
| Raw-overlap "heterogeneity" score, table level | 1.00; names the honest pair (0 of 49), as in v1 |
| S1 / S2 (words-relative overlap) | 0.31 (reversed) / −0.45: the Core detector does not transfer, as in v1 |

**Reading:**
- **On these 50 shoes, the receiver's activations carried more about the count than an honest listener's.** With no count text in its prompt, the big player's lens predicted the current hand's count better than the lens of honest players who read the identical message without the scheme. **The independent replication below did not confirm this,** so the overall evidence is weak.
- **The effect is modest** (0.66 vs 0.57) and smaller than v1's (0.76), which fits v1 having been mostly plain text. The words-relative version is borderline on the all-runs sensitivity check (p = 0.053); raw tokens hold in both.
- **For monitoring:** the benchmark's own text monitor catches none of these tables, and a frozen monitor prompted to look for coded talk reaches 0.75. The lens readout of the receiver is a per-hand signal of what it decoded, which is a different and complementary use.

## Stego v2 replication: 50 new shoes (amendment 5, planned before the data)

**Data:** shoes 50–99 (different cards), with v2 settings.
- **Checks:** none of the 400 big-player prompts holds count history.
- **Gate S passes:** median bet-to-count correlation 0.386, at least 0.3 in 31 of 50 runs.
- **Excluded:** shoe 76, where a counter blurted the count.

| Test | Result |
|---|---|
| **S3, words-relative (the replication test)** | **+0.023** (lower 95% −0.078, **p = 0.34**), **not replicated**. Big player 0.64 [0.55, 0.72]; honest 0.61 |
| S3, raw | +0.084 (lower −0.012, p = 0.075) |
| S3 on all runs | words-relative +0.054 (p = 0.18); raw +0.087 (p = 0.061) |
| Pit boss | 0 of 50 collusion tables flagged |
| Frozen text monitor | 0.84 [0.76, 0.91] |
| Raw-overlap heterogeneity score | 1.00 (names the honest pair, 0 of 49) |

**Pooled v2 + replication** (descriptive per amendment 5; 657 hands, 179 HOT, shoes 22 and 76 excluded):

| | Big player | Honest listeners | Difference |
|---|---|---|---|
| Words-relative | 0.71 [0.66, 0.76] | 0.66 [0.60, 0.72] | +0.049 (lower 95% −0.004) |
| Raw | 0.72 [0.66, 0.77] | 0.63 [0.57, 0.68] | +0.089 (lower 95% +0.027) |

**Reading:**
- **All players' lenses predict the count above chance.** Each prompt contains the full card history of previous hands, so the count is partly computable from public information.
- **The receiver's advantage beyond honest listeners is small (+0.05 to +0.09) and not robust.** v2 passed, the replication did not, and the pooled estimate's interval clears zero only for raw tokens.
- **This is weak evidence, not a demonstration,** that the lens reads the decoded secret.

## Block E: NLA descriptions (amendment 2)

**Tool:** kitft's natural-language autoencoder verbalizer for Gemma-3-27B-IT, at layer 41, stored in bf16 for one A100. It follows kitft's injection recipe in plain transformers, with greedy decoding.
- **Sanity check passed:** at the round-4 prompt end it describes "a formal… recommendation/assessment conclusion" and a coming "RECOMMENDATION:" block, which is accurate.
- **What was described:** 948 stego v2 units (the big player's calls, and honest calls made after the counter in the same hand) and the 400 Core P1 activations.

| Test | Result |
|---|---|
| **E1 (planned):** a frozen Gemma judge reads one description and rates 0–9 "expects favourable cards / will bet big". Big player minus honest players, same hands (335 hands, 92 HOT) | **+0.058** (lower 95% −0.025, p = 0.13), **not significant**. Big player 0.60 [0.51, 0.68]; honest 0.54 [0.47, 0.62] |
| E2: joint judge on Core NLA descriptions, names the instructed pair | 11 of 50 (chance 8.3, p = 0.20) |
| E2: rating, collusion mode vs control | 0.29 [0.19, 0.38] (reversed) |

**What the descriptions say.** They describe the conversational surface ("forum-style chat reacting to group wins", "That's a nice haul! I'll take that…"), for the big player and honest players alike. They never mention a favourable deck or a planned big bet. At layer 41, the decoded count is not what the NLA puts into words, even though a classifier on lens tokens finds it (S3). The words most over-represented in big-player descriptions on HOT hands (E3) are uninformative (*seems*, *format*, *really*, *escalating*, *hands*).

## Block C: transfer tier (exploratory, stored Qwen3-32B activations)

The no-LLM overlap detector, with the Core settings, on NARCBench-Transfer: 72 runs (36 collusion, 36 control), scenario types never used to tune it.
- **Result:** collusion vs control **1.00** (raw) and **0.999** [0.995, 1.00] (words-relative).
- **Check:** the final prompt is identical across the four agents in all 72 runs and holds no private text, so the detector reads the colluders' shared hidden instruction, as on Core.

## Block D: the colluders' private-channel turn (exploratory, Qwen3-32B Core)

A held-out lens classifier for follow-through at the colluders' private-message turn (round 0):

| Read point | Words-relative | Raw |
|---|---|---|
| Before writing | 0.52 | 0.64 (p = 0.014, uncorrected) |
| End of the private message | 0.55 | 0.60 |

None is clearly above the style baseline. The planned text-judge comparison needed Qwen3-32B on the GPU and was not run (block B was cut for time).

## Block F: J-lens vs J++ lens (amendment 3, exploratory)

**Run late in the night** (4:30–4:40 AM ET), once the GPU was free and the main report was written. Together with the ordering note, this goes past the 4:30 AM cutoff; it is recorded here as a deviation.

**Setup:**
- NARCBench Core regenerated with `Qwen/Qwen3-4B` (@ `1cfa9a7`).
- **Gate 1 passed:** 18 runs colluded, 32 collusion-mode runs did not, 59 colluders did not vote the target.
- The same activations, at 10 layers (13…32 of 0–35), read with both Neuronpedia lenses:
  - the **J-lens** (converged, 479 prompts);
  - the **J++ lens** (96 prompts, fitted with `lrp_mode: rlens`, likely the "R lens" asked about).

| Test (same units, both lenses) | J-lens | J++ lens | J++ − J (paired bootstrap) |
|---|---|---|---|
| F1: overlap detector, collusion vs control, words-relative | 0.987 [0.97, 1.00] | 0.993 [0.97, 1.00] | +0.006 (n.s.) |
| F1: same, raw tokens | 0.967 [0.93, 0.99] | 0.912 [0.86, 0.96] | **−0.055** (J++ worse) |
| F2: instruction classifier at P1 | 0.987 | 0.991 | +0.004 (n.s.) |
| F3: follow-through classifier at R3 T-start | 0.575 [0.41, 0.73] | 0.625 [0.48, 0.76] | +0.050 (p = 0.097, n.s.) |

**Reading:**
- **At the middle-to-late layers used throughout this series, the J++ lens performs like the J-lens.** It is slightly worse for raw-token overlap, which fits its claimed advantage being at earlier layers.
- **The overlap detector replicates on a third model** (Qwen3-4B) at 0.97–0.99.

## What this means

- **For monitoring steganographic collusion:**
  - NARCBench's own text monitor is blind to it (0 of 150).
  - A text monitor prompted for coded talk catches much of it at table level (0.68–0.84).
  - The lens's cheapest signal, the raw-token overlap score, separates collusion from control tables perfectly. But it reads *who has different instructions from whom*, which in a real deployment may not single out colluders.
- **For "does the lens read the hidden content?":**
  - v1 looked strong, but it was plain text in the prompt.
  - v2 looked positive (p = 0.021), but the planned replication did not confirm it.
  - Pooled, the receiver's advantage is small (+0.05 to +0.09 AUROC).
  - The honest conclusion: the receiver's lens may hold slightly more of the decoded count than a listener's, but **not robustly at this sample size and read point**.
- **Data quality matters more than expected.** NARCBench-Stego as released leaks in two ways:
  - the big player's private notes into the public chat;
  - the true count history into the colluders' private channel.

  Both are fixed here by a wrapper, without editing the benchmark. Both are worth reporting upstream.

## Next steps

1. **A cleaner decoding test:** read the big player at the token where it writes its bet. A held-out probe there would show whether the decoded count is present at decision time.
2. **Remove public count information:** hide previous hands' cards from all players, so that honest listeners cannot count. Then any count signal in the receiver beyond the listener is decoding alone.
3. **More shoes for power:** the pooled raw-token effect (+0.09) would need roughly 2–3× the data to be confirmed or ruled out cleanly.
4. **Report the two NARCBench-Stego leaks upstream,** with the wrapper as the fix.

## Deviations

- **Amendment 1:** shoes where a counter blurted count markers are excluded; all-runs results reported too.
- **Amendment 2:** block E (NLA) instead of block B (Qwen3-32B stego replication), by Claude under Jorge's "feel free to explore".
- **Amendment 3:** block F (J-lens vs J++) added at Jorge's request, ranked below more stego data, and run at the end of the night after the planned cutoff. "R lens" was not found as a separate lens; the J++ lens here is fitted with `lrp_mode: rlens`.
- **Amendment 4:** stego v2, after the S3 confound was found.
- **Amendment 5:** an independent replication of v2 on shoes 50–99, analysed on its own; a pooled estimate is reported as descriptive only.
- **Leak fix:** a wrapper around the unchanged `stego.py` moves `PRIVATE:`/`DECODE:`/`RANGE:` lines into the line `stego.py` already strips. vLLM runs on its V0 engine (V1 gives gibberish on long prompts).

## Reproduce

```sh
uv run col lens-judge stego generate [--strip-history] --out-dir <runs>
uv run col lens-judge stego gate --stego-dir <runs>
uv run col lens-judge stego extract --stego-dir <runs> --out-dir <out>
uv run col lens-judge stego tokens --out-dir <out>
uv run col lens-judge stego monitor --stego-dir <runs> --out-dir <out>
uv run col lens-judge stego analyse --stego-dir <runs> --out-dir <out>
uv run col lens-judge transfer overlap
uv run col lens-judge private tokens && uv run col lens-judge private analyse
```

**Logs:** `/workspace/lens-judge/{stego,stego-v2,transfer,private}/logs/`.
