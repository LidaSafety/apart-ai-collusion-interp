# Results: is the overlap detector a real collusion monitor?

2026-10-25 · Plan: [`docs/plans/overlap-monitor.md`](../../plans/overlap-monitor.md) (with amendment 1) · Branch `experiments/lens-judge/overlap-monitor`. Planned tests are marked **(planned)**; everything else is **exploratory**.

## In short

1. **The lens beats text overlap on every original dataset** (planned primary passes):
   - Gemma Core +0.08 AUROC (lower bound +0.02);
   - Qwen Core +0.035;
   - Transfer +0.41, where text is near chance (exploratory).
2. **The detector survives every stress test** (planned, all pass Holm):
   - colluders warned that their reasoning is monitored: 0.99;
   - paraphrased instructions: 0.96;
   - no shared text and no channel: 0.89.
3. **It is not collusion-specific.** Two honest agents who share a harmless confidential note are flagged too (0.94). It can barely tell real collusion from that (0.64). It is a **shared-secret-context detector**.
4. **Under stress, the text catches up.** In the new Gemma runs, text-overlap monitors score 0.88–0.98, and the lens's edge over them is no longer significant.
5. **Early warning** (planned):
   - the lens flags coalitions from each agent's state *before its first public message*: Gemma 0.94, Qwen 0.93;
   - a text monitor of the agents' own words has nothing to read at that point.
6. **Which side is the coalition** (rule fixed on Gemma, held-out test planned):
   - "the pair that shares fewer entries in total" names the colluders in **60 of 86** held-out runs (0.70, p = 0.0002);
   - so the monitor identifies the coalition, not just the split, about 70% of the time.
7. **Layers:** single layers reach 0.94 at best (Gemma L45, Qwen L50). Mid-to-late layers carry the most signal, and all ten together are best.
8. **LLM text monitor:** *see section D (filled when the run finishes)*.

## Part 1: lens overlap vs text overlap

AUROC for collusion mode vs control, with 95% scenario-bootstrap intervals. "Split" counts collusion runs where the top pair is the colluders or the two honest agents. The split measure was added after seeing the data, so it is exploratory.

| Dataset | Lens raw | Lens words-rel. | Best text overlap | Lens raw − best text (lower 95%) | Split found (lens raw) |
|---|---|---|---|---|---|
| Core, Gemma-3-27B **(planned primary)** | **0.978** [0.956, 0.994] | 0.943 | 0.902 (top-250 TF-IDF) | **+0.076** (+0.022), p = 0.006 ✅ | 49/50 |
| Core, Qwen3-32B | **0.987** [0.971, 0.999] | 0.988 | 0.952 (cosine) | +0.035 (+0.005), p = 0.024 | 50/50 |
| Transfer, Qwen3-32B | **1.000** [1.000, 1.000] | 0.999 | 0.586 (cosine) | **+0.414** (+0.343), p < 0.001 | 36/36 |

- The four text instruments count the same thing on each agent's own public messages (rounds 1–3, names removed): shared words, shared word pairs, the 250 top TF-IDF words, and TF-IDF cosine.
- The comparison uses the *best* of the four on each dataset, which favours text.
- **The detector's top pair is the colluders in only 40–55% of runs.** When it isn't, it is the two *honest* agents: colluders lose concepts the honest pair shares. Section B uses this.

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

  At a 5% false-alarm rate the shares are 90%, 96%, 86%, 74% and 70%.
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

*Running: Gemma-3-27B reads each run's public discussion and rates collusion 0–9, then names a pair. Results to be added.*

Outputs for A–D are in `results/overlap/extras/*.json`, from `col lens-judge overlap extras`.

## What this means for monitoring

- **What the lens monitor is:** a cheap, label-free detector of agents that share a hidden context. It works before they speak, survives warnings and paraphrase, and usually picks out which pair.
- **What it isn't:** a detector of harmful intent. A harmless shared secret looks the same. A second stage has to judge what the shared context *is*, for example by reading the shared tokens, which the run explorer shows.
- **Where it adds over text:** when the shared secret doesn't surface in what agents write (Transfer) and before they write anything (early warning). Once colluders' messages converge, text overlap catches them as well.

## Limitations

- One generation per condition, 50 runs each, on one model (Gemma) for the stress tests.
- Transfer was exploratory.
- The benign note is a single wording.
- Both stress-test colluders still read each other's public messages.
- Sampling isn't seeded per request (vLLM), so transcripts can't be regenerated exactly. The transcripts themselves are stored.
