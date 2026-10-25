---
name: simple-teach
description: Explain ONE concept as a single self-contained HTML file in the workspace root — no curriculum, no extra files. Use when the user asks for a quick illustrated explainer ("simple teach", "illustrate this in an html", "make me a simple html explaining X").
disable-model-invocation: true
argument-hint: "What should the explainer cover?"
---

The user wants a one-off illustrated explainer, NOT a multi-session curriculum (that is `/teach`). Produce **exactly one self-contained HTML file** and nothing else.

## Hard rules

- **One file, zero scaffolding.** Write `<topic-kebab-case>.html` into the workspace root, next to any existing explainers (e.g. `example.html`, `harness-lessons.html`). Never create `lessons/`, `learning-records/`, `MISSION.md`, `RESOURCES.md`, `NOTES.md`, or any directory/file beyond the one HTML, unless prompted by the user.
- **Self-contained:** inline CSS, optional vanilla JS. Math via **KaTeX** CDN auto-render with LaTeX delimiters (`$...$`, `$$...$$`) — never plain-Unicode math. (KaTeX renders synchronously with no load-flash and matches the existing explainers; reach for MathJax only if you need niche LaTeX packages or built-in screen-reader accessibility.)
- **Real artifacts, labeled hypotheticals.** Anything presented as *fact* — dataset rows, code, command output, version numbers — must be pulled from the actual files (Read/Bash) before writing, never recalled from memory. *Constructed* examples (a proof a model might submit, an adversarial counterexample, a counterfactual run) are allowed and often essential — but visibly label them as hypothetical, and make sure they are faithful (they would actually behave as claimed; type-check the logic).
- **One thing.** The file teaches the single concept asked about, scoped to be readable in ~5 minutes. If an existing explainer HTML already covers it, extend or link that file instead of duplicating.

## Teaching principles (ported from /teach)

- **Verify, don't assume.** Never trust parametric knowledge for a teachable claim — check the project files or a trusted source first, and cite it. Every external claim gets a link; the footer collects sources so the reader has a path to go deeper.
- **Knowledge first, then practice.** Teach the mechanism, then make the reader *use* it. Include interactive checks with immediate feedback — aim for **at least 2 open-ended questions and at least 2 multiple-choice (MCQ) questions**. Use `<details>/<summary>` scenario quizzes at minimum; light in-browser tasks (click-to-check, predict-the-output, MCQ with clickable options) where vanilla JS suffices. The feedback loop should be as tight as possible — answer revealed right where the question is asked.
- **Concrete over abstract.** Every mechanism gets a worked walk-through with real values flowing through it (the "one full turn through the pipeline" style). Prefer showing the exact failing text with the load-bearing token highlighted over describing the failure.
- **Define every symbol — including its index range and locus.** No equation may introduce notation the reader hasn't been given. The first time a symbol appears, define it right there — an inline clause, a "where …" list under the display equation, or a small glossary table — or explicitly point to the sibling doc that defined it (e.g. "$v$ as in `reference-grafting.html`"). A formula whose terms (e.g. $p_q^S$, $S$) are undefined teaches nothing; spell out every variable, sub/superscript, and set. This extends past lone variables to **three things that hide in plain sight**: (i) **summation/index ranges** — when you write $\sum_i c_i$, say what $i$ ranges over (which set, how many terms); (ii) **the bare-vs-indexed relationship** — if the same letter appears alone and subscripted ($c$ vs $c_{\text{head}}$ vs $c_{\text{MLP}}$), state that the bare form is the generic/template and the subscripts are its instances, not new objects; (iii) **the locus** — when a quantity depends on layer / token position / timestep, say *which* (e.g. is $\sum_{\text{MLPs}} c_{\text{MLP}}$ over *all* layers or just the last? measured at *which* token position?). A sum whose index set or evaluation point is unstated is as undefined as an unlabelled variable — verify each formula against all three before writing it.
- **Visual where structure matters.** Tick/cross tables for configurations, highlighted spans in code blocks, before/after contrasts. Clean, print-friendly typography (serif body, monospace code, restrained palette) — the file should be beautiful enough to reread.
- **A tangible quick win.** The reader should leave able to *do* something specific (spot the row shape, predict the verdict, fix the loader) — not just "aware of" the topic.
- **Zone of proximal development.** Build on what the reader has already demonstrated in the conversation; don't re-teach established ground, and don't assume unestablished ground — explain CS/Lean/tooling machinery from scratch, keep the mathematics at grad-level rigor.
- **Invite follow-ups.** End with a reminder that the agent is the teacher: unclear points, deeper dives, and "why" questions go back to the chat.

## Finish

End your reply with the one-line open command, e.g. `open <absolute-path>.html`, and a 3–5 bullet summary of what the file teaches. Do not propose a lesson series.
