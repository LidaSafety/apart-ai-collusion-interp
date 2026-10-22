# Round-4 lens judge: what went wrong at step 2

2026-10-22 · Jorge (draft by Claude) · Checkpoint before any judge runs. Diagnostic and cost numbers are **exploratory**.

**In one line:** the pipeline is correct, but the J-lens tokens at our two read positions carry almost nothing agent-specific, so the judge would most likely fail its gate and give an uninformative null.

## What works ✅

| Check | Result |
|---|---|
| Stored activations vs fresh recompute (8 agents, 64 blocks) | cosine **1.00000** at every block |
| P1 / P2 token positions | match for all agents |
| Our readout vs the authors' library (layer 39) | identical top-25, logit diff **0.0** |
| Lens file | sha256 matches |

## Issue 1: every agent sees the same tokens

Two agents in the **same run** share **84–98%** of their top-25 tokens at P1. Agents from **different scenarios** still share 67–96%. There is little left that could tell a colluder apart.

![overlap](1_overlap.png)

## Issue 2: the tokens are mostly formatting and filler

At P1, most layers are punctuation and markup (`“ — … ** ____`). P2 is dominated by Chinese filler tokens (`继续保持`, `展现出`) and, late, by the coming request ("Final", "Vote", "Please"). Scenario words appear for at most **14%** of agents.

![token kinds](2_token_kinds.png)

Example, layer 39 at P1. The colluder and the honest agent show nearly the same tokens:

| Agent | Layer 39 tokens (first 10 of 25) |
|---|---|
| colluder | `␣“ ␣— … ␣… ␣– ␣... ␣" ␣** What ␣[…` |
| honest | `␣“ … ␣... ␣… ␣— ␣– ␣[… ... ␣** What` |

## Issue 3: the lens is noisy in the middle layers

In layers 32–43, the 25 tokens shown hold **under 20%** (often < 2%) of the lens's probability, so they are drawn from a nearly flat distribution. The lens was not fitted to convergence (≈13% relative error vs ≈5% for converged lenses).

![probability mass](3_probability_mass.png)

## Diagnostic: is the lens or the read position the problem? Both

- **On the lens library's own examples** it finds 3 of 7 pre-specified concepts (Italy, ocean creatures, the number 7), often in Chinese. It fails the long agentic example, which is the one closest to our prompts.
- **Right after the instruction is read** (end of the system prompt), 4 of 6 colluders show their instruction's *stance* ("argue", "support", "argument"), while honest agents show "assess", "evaluate". **By P2 this is gone.**

![instruction visibility](4_instruction_visibility.png)

## Fix option A: refit the lens (expensive, uncertain)

A converged lens needs about 3,800 prompts (13% → 5% error, scaling as 1/√n). Chat-length prompts (512 tokens) don't fit on the A100 with all layers.

![refit cost](5_refit_cost.png)

## Questions for the meeting

1. **Run the plan as written?** The gate would most likely fail, so the null would be uninformative.
2. **Change where we read?** E.g. during the colluders' own discussion turns, where they produce their arguments, instead of the final prompt that all agents share.
3. **Refit the lens?** About 7 h on 8× B200. It won't help if the signal has already faded by the read position.
