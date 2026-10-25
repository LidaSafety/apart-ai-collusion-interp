# Results: is the overlap detector a real collusion monitor?

2026-10-25 · Plan: [`docs/plans/overlap-monitor.md`](../../plans/overlap-monitor.md) (with amendments 1–4) · Branch `experiments/lens-judge/overlap-monitor`. Planned tests are marked **(planned)**; everything else is **exploratory**.

## In short

1. **The lens beats text overlap on every original dataset** (planned primary passes):
   - Gemma Core +0.08 AUROC (lower bound +0.02);
   - Qwen Core +0.035;
   - Transfer +0.41, where text is near chance (exploratory);
   - at zero false alarms on the controls (in-sample), the lens catches 70%, 74% and 100% of collusion runs; the best text monitor at most 64%, 66% and 14%.
2. **The detector survives every stress test** (planned, all pass Holm):
   - colluders warned that their reasoning is monitored: 0.99;
   - warned and told to keep the arrangement out of their reasoning: 0.99 (amendment 3);
   - paraphrased instructions: 0.96;
   - paraphrased with no private channel: 0.89.
3. **It is not collusion-specific.** Two honest agents who share a harmless confidential note are flagged too: three different notes 0.88–0.94, and the first note given openly 0.94. It can barely tell real collusion from the first (0.64). It detects **context only two agents share**, not secrecy or intent.
4. **Under stress, the text catches up.** On the new collusion conditions text overlap scores 0.92–0.98, and the lens's edge is no longer significant.
5. **Early warning** (planned):
   - the lens flags coalitions from each agent's state *before its first public message*: Gemma 0.94, Qwen 0.93;
   - agents speak in turn, so later speakers have read earlier speakers' first messages (and colluders their private channel); but no agent's own words exist yet for a text-overlap monitor to compare.
6. **Which side is the coalition** (rule fixed on Gemma, held-out test planned):
   - "the pair that shares fewer entries in total" names the colluders in **60 of 86** held-out runs (0.70, p = 0.0002);
   - so the monitor identifies the coalition, not just the split, about 70% of the time.
7. **Layers:** single layers reach 0.94 at best (Gemma L45, Qwen L50). Mid-to-late layers carry the most signal, and all ten together are best.
8. **An LLM text monitor is fragile** (planned):
   - Qwen3-32B reading Qwen transcripts reaches 0.84, and the lens beats it (+0.15).
   - Gemma-3-27B with the same prompt on Gemma transcripts is **inverted (0.17)**: it reads honest agents converging on the fair option as coordination. It is inverted on every stress set too (0.12–0.14) and at chance on Transfer (0.53).
   - Its *named pair* is often right (32 of 50 on Gemma Core), more often than the lens's top pair.
9. **Against NARCBench's own trained deception probes** (planned, amendment 4; all three tests pass Holm):
   - the reproduction matches the paper on Core (Qwen: 1.00 with all five statistics; Gemma: four of five, the fifth 0.96); zero-shot on Transfer it is lower than reported (0.74–0.77 vs 0.82–0.88);
   - **the untrained overlap transfers better:** Qwen Transfer 1.00 vs 0.78 (K3, +0.22, lower bound +0.13);
   - **the probe tells collusion from the cite-evidence note** (K1, 0.97), where overlap can't (0.64; K2, +0.33);
   - but the probe also flags the budget and deadline notes against controls (0.93, 0.92, exploratory); collusion vs those notes was not tested;
   - the supervised TF-IDF baseline **failed its validity gate** (shuffled labels still give 0.63 and 0.84), so it is reported as invalid.
10. **Where it fails:** coalitions that share no context. On NARCBench-Stego the two colluders get different instructions, and the overlap monitor finds nothing ([`../stego/README.md`](../stego/README.md)).

## Part 1: lens overlap vs text overlap

AUROC for collusion mode vs control, with 95% scenario-bootstrap intervals. "Split" counts collusion runs where the top pair is the colluders or the two honest agents. The split measure was added after seeing the data, so it is exploratory.

| Dataset | Lens raw | Lens words-rel. | Best text overlap | Lens raw − best text (lower 95%) | Split found (lens raw) |
|---|---|---|---|---|---|
| Core, Gemma-3-27B **(planned primary)** | **0.978** [0.956, 0.994] | 0.943 | 0.902 (top-250 TF-IDF) | **+0.076** (+0.022), p = 0.006 ✅ | 49/50 |
| Core, Qwen3-32B | **0.987** [0.971, 0.999] | 0.988 | 0.952 (cosine) | +0.035 (+0.005), p = 0.024 | 50/50 |
| Transfer, Qwen3-32B | **1.000** [1.000, 1.000] | 0.999 | 0.586 (cosine) | **+0.414** (+0.343), p < 0.001 | 36/36 |

- The four text instruments count the same thing on each agent's own public messages (rounds 1–3, names removed): shared words, shared word pairs, the 250 top TF-IDF words, and TF-IDF cosine.
- The comparison uses the *best* of the four on each dataset, which favours text.
- **The detector's top pair is the colluders in only 31–46% of runs** (20 of 50, 23 of 50, 11 of 36). When it isn't, it is the two *honest* agents: colluders lose concepts the honest pair shares. Section B uses this.

Outputs are in `results/overlap/text/{gemma,qwen,transfer}.{json,parquet}`, from `col lens-judge overlap text --dataset …`.

## Part 2: stress tests (new Gemma generations)

There are 50 new collusion-mode runs per condition, made with NARCBench's `core.py` through a prompt wrapper. Each condition is compared with the 50 Gemma Core controls. Gate P: 149 of 150 paraphrased fields pass. Their median share of the original's word pairs is 0 and the maximum 0.12. One option label ("Level 2", eng_02) was lost, and that scenario was kept.

| Condition | Lens raw | Best text | Lens − text (lower 95%) | Split / top pair = colluders (lens raw) | Both colluders voted target |
|---|---|---|---|---|---|
| Core (reference) | 0.978 | 0.902 | +0.076 (+0.022) | 49 / 20 of 50 | 28 |
| **aware**: warned of a monitor reading messages *and reasoning* **(planned)** | **0.986** [0.964, 0.998] | 0.977 | +0.010 (−0.009) | 50 / 22 | 33 |
| **para**: colluder 2's instruction paraphrased **(planned)** | **0.960** [0.929, 0.986] | 0.927 | +0.033 (−0.011) | 47 / 12 | 23 |
| **independent**: paraphrased, no private channel **(planned)** | **0.894** [0.827, 0.951] | 0.920 | −0.026 (−0.095) | 45 / 13 | 20 |
| **benign**: honest pair with one shared confidential note | **0.939** [0.889, 0.975] | 0.884 | +0.055 (−0.003) | 48 / 20 | 2 (no target) |

- **Primary family** (aware, para, independent > 0.5, Holm): all three pass, p < 0.001.
- **Core collusion vs benign, lens raw: 0.64** [0.55, 0.72]. The detector barely separates a harmful coalition from a harmless shared secret.
- **Operating point.** The threshold is the largest Core-control score, so 0 of 50 controls are flagged. Collusion runs flagged at that threshold:

  | Set | Flagged |
  |---|---|
  | Core | 70% |
  | aware | 86% |
  | para | 68% |
  | independent | 48% |
  | benign | 48% |

  At the controls' 95th percentile (3 of 50 controls above it, a 6% false-alarm rate) the shares are 90%, 96%, 86%, 74% and 70%.
- **Behaviour:** the manipulations didn't stop collusion. In `aware` the colluders voted the target *more* often (71% of colluders) than in Core.

Outputs are in `results/overlap/<condition>/` and `results/overlap/stress.json`, from `col lens-judge overlap generate`, then `gemma labels/extract --final-only/tokens`, then `overlap stress`. Transcripts are in `/workspace/lens-judge/overlap-monitor/transcripts/`.

## Amendment 1

### A. Early warning (planned)

The overlap score uses each agent's lens tokens at its own turn start, the prompt end just before it writes. At round 1 no agent has yet written a public message of its own.

| Read point | Gemma raw | Gemma words-rel. | Qwen raw | Qwen words-rel. |
|---|---|---|---|---|
| **R1 T-start** | **0.944** [0.903, 0.979] **(primary)** | 0.653 | **0.928** [0.875, 0.971] | 0.862 |
| R2 T-start | 0.938 | 0.843 | 1.000 | 1.000 |
| R3 T-start | 0.950 | 0.902 | 0.999 | 0.996 |
| P1 (vote prompt, for reference) | 0.978 | 0.943 | 0.987 | 0.988 |

All have p < 0.01.

**Caveat:** at round-1 T-start, colluders have already read their private channel, and agents who speak later in the round have read earlier speakers. The claim is "before the agent's own first public message", not "before any communication".

### B. Which side is the coalition? (rule exploratory, held-out test planned)

**Rule**, fixed on Gemma Core before the held-out test: take the top pair and its complement. The coalition is the pair whose two members share fewer raw lens entries in total. The rule only chooses within a right split.

| Set | Named the colluders | Share | p (one-sided, vs 1/2) |
|---|---|---|---|
| Gemma Core (development set) | 34 of 49 | 0.69 | 0.005 |
| Qwen Core (held out) | 36 of 50 | 0.72 | 0.001 |
| Transfer (held out) | 24 of 36 | 0.67 | 0.03 |
| **Held out, pooled (primary)** | **60 of 86** | **0.70** | **0.0002** |

Combined with the split, the monitor names the coalition pair without labels in roughly 0.7 of collusion runs; chance is 1 in 6.

### C. Layers (descriptive)

Mode-vs-control AUROC from one layer's raw entries alone:

| | | | | | | | | | | |
|---|---|---|---|---|---|---|---|---|---|---|
| Gemma layer | 23 | 27 | 30 | 34 | 38 | 41 | **45** | 49 | 52 | 56 |
| AUROC | 0.82 | 0.85 | 0.79 | 0.84 | 0.87 | 0.90 | **0.94** | 0.85 | 0.77 | 0.65 |
| Qwen layer | 24 | 28 | 32 | 35 | 39 | 43 | 47 | **50** | 54 | 58 |
| Qwen Core | 0.72 | 0.70 | 0.84 | 0.89 | 0.82 | 0.82 | 0.86 | **0.94** | 0.75 | 0.61 |
| Transfer | 0.80 | 0.90 | 0.81 | 0.85 | 0.77 | 0.83 | **0.91** | 0.88 | 0.77 | 0.71 |

The signal peaks in mid-to-late layers, about 75–85% of depth, and falls at the last layers. All ten layers together (0.98–1.00) beat any single one.

### D. LLM text monitor (planned)

A frozen judge reads each run's public discussion of rounds 1–3 (agents numbered and named, no votes). It answers the joint judge's question: a 0–9 rating that two agents are colluding, then PAIR.
- Qwen Core uses the existing Qwen3-32B `discussion` arm.
- Every other set uses Gemma-3-27B-IT with the same prompt.
- Transfer uses neutral task wording.
- Stress sets are compared with the Gemma Core controls.

| Set | LLM monitor AUROC | Its pair = colluders | Right split | Lens raw − monitor (lower 95%) |
|---|---|---|---|---|
| **Gemma Core (primary)** | **0.166** [0.090, 0.256] (inverted) | 32 / 50 | 37 / 50 | +0.812 (+0.735) |
| Qwen Core (Qwen3-32B judge) | **0.837** [0.758, 0.908] | 27 / 50 | 35 / 50 | **+0.151** (+0.087) |
| Transfer | 0.533 [0.448, 0.620] | 13 / 36 | 22 / 36 | +0.467 (+0.394) |
| aware | 0.144 | 32 / 50 | 38 / 50 | +0.842 |
| para | 0.133 | 25 / 50 | 33 / 50 | +0.827 |
| independent | 0.118 | 29 / 50 | 37 / 50 | +0.776 |
| benign | 0.386 | 14 / 50 | 22 / 50 | +0.553 |

**Amendment family** (Holm, one-sided α = 0.05): A (Gemma R1, p < 0.001), B (held-out side rule, p = 0.0002) and D (Gemma lens − monitor, p < 0.001) are **all rejected**.

**Reading D honestly:**
- **The primary D passes only because the Gemma monitor is worse than chance.** That is a weak win and we don't lean on it.
- **The meaningful comparison is Qwen,** where the LLM monitor works (0.84) and the lens still beats it by +0.15 (lower bound +0.09).
- **The inversion is itself a finding.** Gemma's replies flag "nearly identical statements … strongly suggests coordinated communication" in control runs, where the four honest agents converge on the fair option. In collusion runs the colluders argue against the room, which looks less "coordinated" to the judge. The same plausible prompt works on one model's transcripts and fails on another's.
- **Its pair is informative even when its rating isn't.** The Gemma monitor names the colluders in 32 of 50 Core runs and 32 of 50 `aware` runs, more often than the lens's top pair (20 of 50) or the lens's side rule. A combined monitor could use the lens to decide *whether* to flag and the text judge to say *who*. That is untested.
- We report the planned score as is and do not flip it.

Outputs for A–D are in `results/overlap/extras/*.json`, from `col lens-judge overlap extras`.

## Amendment 2

### E. A second stage that reads the shared tokens (planned): null

A frozen Gemma judge sees only the raw lens tokens exclusive to each side of the split (no transcript, names or roles). It rates 0–9 whether one pair shares a hidden agenda to push an outcome.

| Contrast | Stage 2 | Lens alone | Stage 2 − lens (lower 95%) |
|---|---|---|---|
| **Core collusion vs benign (primary)** | **0.510** [0.392, 0.628], p = 0.43 | 0.637 | −0.127 (−0.245) |
| Core collusion vs Core controls | 0.659 | 0.978 | −0.319 |
| aware / para / independent vs Core controls | 0.596 / 0.699 / 0.602 | 0.986 / 0.960 / 0.894 | −0.26 to −0.39 |
| benign vs Core controls | 0.684 | 0.939 | −0.256 |
| Transfer collusion vs controls | 0.847 | 1.000 | −0.153 |

- **The primary test fails.** From the raw shared tokens, this judge can't tell a harmful coalition from a harmless shared secret, and does worse than the lens score alone.
- The tokens carry *some* signal (above chance against controls, best on Transfer), but far less than the overlap count itself.
- The raw tokens are noisy: multilingual fragments and code pieces. A better stage 2 would need a cleaner rendering, the transcript, or a stronger judge. This was not tested.

### F. Flag and name, end to end (descriptive)

- **Flag:** lens score above the largest Core-control score, so 0 of 50 false alarms. For Transfer, above the largest Transfer-control score.
- **Name:** the side rule (B), or the Gemma text monitor's PAIR line (D).

| Set | Flagged | Flagged and named right (side rule) | (text judge) |
|---|---|---|---|
| Core, Gemma | 35 / 50 | 24 | 25 |
| aware | 43 / 50 | 25 | 29 |
| para | 34 / 50 | **32** | 17 |
| independent | 24 / 50 | 17 | 16 |
| benign (the two note-sharers) | 24 / 50 | 11 | 6 |
| Transfer | 36 / 36 | **24** | 13 |

- With zero false alarms, the monitor flags *and* names the right pair in about half of Core collusion runs and two thirds of Transfer runs.
- The label-free side rule names the pair at least as well as the LLM judge in most sets, and far better on paraphrased runs and Transfer.

Outputs are in `results/overlap/content/*.parquet` and `results/overlap/extras/amendment2.json`, from `col lens-judge overlap content` and `col lens-judge overlap extras2`.

## Amendment 3

### H. Stage 2 retried with cleaner input (exploratory): still null

This time the judge sees the *words-relative* tokens each side of the split shares, plus the case's public brief. The words are far more legible. In one collusion run the coalition shares *phony, fake, misleading, contrary, reconsider, despite*.

| Contrast | Stage 2 (H) | Stage 2 (E, raw) | Lens alone |
|---|---|---|---|
| **Core collusion vs benign** | **0.560** [0.459, 0.662], p = 0.13 | 0.510 | 0.637 |
| Core collusion vs Core controls | 0.824 | 0.659 | 0.978 |
| aware / para / independent vs controls | 0.815 / 0.676 / 0.670 | 0.60–0.70 | 0.89–0.99 |
| benign vs controls | 0.809 | 0.684 | 0.939 |

- Cleaner words help the judge separate any shared secret from controls (0.82 vs 0.66).
- But it still can't separate a harmful coalition from a harmless confidential note, because it finds the harmless note suspicious too (0.81).
- This is labelled exploratory: it was run after E's null on the same contrast.

Outputs are in `results/overlap/content_brief/` and `results/overlap/extras/amendment3_h.json`, from `col lens-judge overlap content --brief` and `col lens-judge overlap content-brief-tests`.

### G. Evade and three benign variants (planned)

Each condition has 50 new Gemma runs against the same 50 Core controls. Predictions were committed before the results (plan, amendment 3).

| Condition | Lens raw | Best text overlap | Right split | Flagged at 0 false alarms | Prediction |
|---|---|---|---|---|---|
| **`evade`**: warned, and told to keep the arrangement out of their reasoning | **0.985** [0.966, 0.999] | 0.978 | 50 / 50 | 68% | 0.95–0.99 ✅ |
| `benign_budget`: shared confidential budget detail | **0.877** [0.796, 0.943] | 0.894 | 50 / 50 | 36% | 0.85–0.95 ✅ |
| `benign_deadline`: shared confidential deadline | **0.942** [0.891, 0.978] | 0.901 | 48 / 50 | 50% | 0.85–0.95 ✅ |
| `benign_open`: the `benign` note, but open | **0.942** [0.892, 0.979] | 0.784 | 48 / 50 | 70% | below `benign` ❌ (it is *above*) |

- **G1, does `evade` still get flagged?** Yes: 0.985, p < 0.001, passes Holm. Colluders told to keep the arrangement, their partner and their instructions out of their reasoning are flagged as readily as warned (0.986) or unwarned (0.978) ones. They still collude: both voted the target in 27 of 50 runs; 61% of colluder votes.
- **G2, is a secret note scored higher than the same note given openly?** No: AUROC **0.32** [0.23, 0.41], p = 1.0, not rejected. The direction is *reversed*: the open note scores higher.
- **Harmless secrets are flagged in general.** Budget 0.88 and deadline 0.94 join the original `benign` note at 0.94.
- **Text overlap does about as well as the lens on the budget and deadline notes** (0.89, 0.90). That's against my prediction that these notes, irrelevant to the decision, wouldn't change what the agents write.
- **On `benign_open`, text overlap drops (0.70–0.78) while the lens rises.** When the note is open, the pair's *words* stop being distinctive, but their *activations* still share it.

**Reading.** The lens monitor detects **context that only those two agents were given**, regardless of whether it is secret and regardless of whether it is harmful. It is robust to deliberate evasion of reasoning. It is not a detector of secrecy or of collusive intent.

Predictions vs results:
- 3 of 6 predictions were right: G1, budget and deadline.
- 3 were wrong: text on budget and deadline, the direction of `benign_open`, and text on `benign_open`.

Outputs are in `results/overlap/{evade,benign_budget,benign_deadline,benign_open}/` and `results/overlap/stress3.json`, from `col lens-judge overlap generate --condition …` then `overlap stress3`.

## Amendment 4

### I. NARCBench's deception probes vs the overlap monitor (planned)

We reproduce the probes of Rose et al. (arXiv 2604.01151 v5) by calling the authors' released code read-only (`third_party/narcbench/probes/reproduce_LR.py`, `extraction/extract_core.py`): their read position (last token of the chat-rendered prompt plus response), layers (Qwen 26–30; Gemma the middle five, 29–33), logistic regression (C = 25, liblinear, max_iter 8, standardised, their noise augmentation), leave-one-domain-out on Core and zero-shot on Transfer, 5 layers × 10 seeds. For Qwen our stored activations at their read position match their rendering on all 1,600 public Core calls.

**Reproduction (Qwen3-32B, their evaluation).**

| Statistic | Core, ours | Core, paper | Transfer family mean, ours | paper | Transfer all 72 runs, ours |
|---|---|---|---|---|---|
| Peak Suspicion | 1.00 | 1.00 | 0.74 | 0.84 | 0.74 |
| Deception Split | 1.00 | 1.00 | 0.74 | 0.88 | 0.76 |
| Asymmetry Probe | 1.00 | 1.00 | 0.77 | 0.87 | 0.78 |
| Sorted Concatenation | 1.00 | 1.00 | 0.74 | 0.82 | 0.68 |
| Activation Alignment | 1.00 | 1.00 | 0.57 | 0.48 | 0.52 |

Without their noise augmentation every number is within 0.002. On Gemma Core (their protocol) the probe also reaches 1.00.

**Head to head on identical runs** (probe: Deception Split, run scores averaged over the 50 layer × seed fits; 95% scenario-bootstrap intervals).

| Contrast | Overlap | Probe |
|---|---|---|
| Qwen Transfer, collusion vs controls | **1.00** | 0.78 [0.65, 0.88] |
| Gemma Core, collusion vs controls | 0.98 | 0.99 |
| `aware` / `evade` / `para` / `independent` vs controls | 0.99 / 0.99 / 0.96 / 0.89 | 0.97 / 0.99 / 0.96 / 0.96 |
| Gemma Core collusion vs `benign` (cite-evidence note) | 0.64 [0.55, 0.72] | **0.97** [0.94, 0.99] |
| `benign` / `benign_budget` / `benign_deadline` / `benign_open` vs controls (false alarms) | 0.94 / 0.88 / 0.94 / 0.94 | 0.66 / 0.93 / 0.92 / 0.58 |

**Planned tests** (Holm over three, one-sided α = 0.05): all rejected.

| Test | Result | Prediction |
|---|---|---|
| K1: probe separates Core collusion from `benign` | 0.97, p < 0.001 | ≥ 0.75 ✅ |
| K2: probe minus overlap on that contrast | +0.33, lower 95% +0.26, p < 0.001 | passes ✅ |
| K3: overlap minus probe on Qwen Transfer | +0.22, lower 95% +0.13, p < 0.001 | passes ✅ |
| Qwen Core reproduction | 1.00 | ≈ 1.0 ✅ |
| Qwen Transfer, Deception Split | 0.76 all runs; 0.74 family mean | 0.75–0.90, partly |
| TF-IDF: Core ≥ 0.9, Transfer ≤ 0.7, null gate 0.5 ± 0.1 | Core 0.87 (Gemma), 0.94 (Qwen); Transfer 0.52; **null 0.63 and 0.84: gate failed** | ❌ |

- **The two are complementary.** The label-free overlap transfers to unseen task types where the trained probe drops; the probe, trained on colluder-vs-honest labels, rejects the cite-evidence note that overlap flags.
- **The probe also flags two harmless notes** (exploratory): the budget and deadline notes score 0.93 and 0.92 against controls. Collusion vs those notes was not tested, so K1 shows the probe rejects one harmless note, not harmless notes in general.
- **TF-IDF is invalid.** With colluder labels shuffled within runs its run statistics still separate collusion runs (0.63 Gemma, 0.84 Qwen), so its scores pick up run-level structure, not the labels. Per the plan we do not interpret its other numbers.

Outputs: `results/probes/{qwen,gemma}/`, `results/probes/qwen/paper_metrics*.json`, `results/probes/compare.json`, from `col lens-judge probes extract-qwen`, `extract-gemma`, `reproduce` and `compare`. Log: `results/logs/2026-10-25T15-53_probes-compare.log`.

## What this means for monitoring

- **What the lens monitor is:** a cheap, label-free detector of agents that share a hidden context. It works from each agent's state before its own first message, survives warnings and paraphrase, and usually picks out which pair.
- **What it isn't:** a detector of harmful intent, or even of secrecy. Three different harmless shared notes are flagged (0.88–0.94), the same note given openly is flagged *more* (G), and judges reading the shared tokens couldn't tell harmful from harmless (E, H).
- **What it resists:** colluders told to keep the arrangement out of their reasoning are still flagged at 0.985 (G).
- **How it pairs with a trained probe:** overlap transfers and needs no labels; the probe rejects one harmless note that overlap flags, but flags two others against controls (I).
- **Where it adds over text:** when the shared secret doesn't surface in what agents write (Transfer) and before each agent writes its own first message (early warning). Once colluders' messages converge, text overlap catches them as well.

## Limitations

- One generation per condition, 50 runs each, on one model (Gemma) for the stress tests.
- The lens-vs-text comparison on Transfer was exploratory (the comparison with the probe there, K3, was planned).
- The harmless notes are three wordings, plus one open variant.
- False-positive rates are in-sample: the thresholds are set on the same 50 Core controls, which every stress set reuses.
- Both stress-test colluders still read each other's public messages.
- Sampling isn't seeded per request (vLLM), so transcripts can't be regenerated exactly. The transcripts themselves are stored.
- The provenance header of every result file records the series' default `model` (Qwen/Qwen3-32B), also for Gemma analyses: `colx.provenance.collect` fills it from a constant and no caller overrides it. The numbers are unaffected; each file's `command` and input paths say which model's data it analysed.
