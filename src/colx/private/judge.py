"""Block D's text comparison: a frozen judge reads the private messages a colluder had seen.

For each colluder, the private-channel messages up to and including its own (the first
colluder sees only its own, the second sees its partner's too): what its P-end activation
had read. Prompt, question and score as follow-up B (`colx.turns.textjudge`).
"""

from pathlib import Path

import pandas as pd

from colx import provenance
from colx.turns.textjudge import load_judge, score_prompts, text_prompt


def seen_private(private_messages: list[str], name: str) -> list[str]:
    """Private messages up to and including the agent's own."""
    own = next(i for i, m in enumerate(private_messages) if m.startswith(f"[{name}]: "))
    return private_messages[: own + 1]


def prompt_table(colluders: pd.DataFrame, runs: pd.DataFrame, private: dict) -> pd.DataFrame:
    """One prompt per colluder."""
    brief = runs.set_index("run_id")["brief"]
    return pd.DataFrame(
        [
            {
                "run_id": c.run_id,
                "agent": c.agent,
                "prompt": text_prompt(
                    brief[c.run_id],
                    seen_private(private[c.run_id], c.agent),
                    c.agent,
                    c.target_option,
                ),
            }
            for c in colluders.itertuples()
        ]
    )


def run_private_judge(
    model_path: str, colluders, runs, private: dict, out_dir: Path, judge: str, log=print
) -> dict:
    """Score every colluder; save `private_judge.parquet`."""
    table = prompt_table(colluders, runs, private)
    tokenizer, model, render = load_judge(judge, model_path)
    tokenizer.padding_side = "left"
    scores = score_prompts(model, tokenizer, render, table, log)
    scores.to_parquet(out_dir / "private_judge.parquet", index=False)
    provenance.write_meta(
        out_dir / "private_judge.parquet",
        provenance.collect("col lens-judge private judge", judge=judge, label="exploratory"),
    )
    mass = scores.p_yes + scores.p_no
    return {"prompts": len(scores), "min P(Yes)+P(No)": round(float(mass.min()), 3)}
