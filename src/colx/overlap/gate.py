"""Gate P of the overlap-monitor plan: are the paraphrases really differently worded?

Per scenario and field (motive, instruction, lowkey instruction): the share of the
original's word bigrams (stop words removed, as in `overlap.text`) that reappear in the
paraphrase, and whether every option label of the original survives. Pass: labels kept
and bigram share < 0.2. Failing scenarios are listed and kept (the gate measures the
manipulation; it does not select data).
"""

import json
from itertools import pairwise
from pathlib import Path

from colx.overlap.text import words
from colx.overlap.variants import PARAPHRASED, option_labels

MAX_SHARE = 0.2


def bigram_share(original: str, paraphrase: str) -> float:
    """Share of the original's word bigrams that also occur in the paraphrase."""
    a, b = set(pairwise(words(original))), set(pairwise(words(paraphrase)))
    return len(a & b) / len(a) if a else 0.0


def check(scenarios: list[dict], paraphrases: dict) -> list[dict]:
    """One row per scenario and field: bigram share, labels kept, pass."""
    rows = []
    for s in scenarios:
        for field in PARAPHRASED:
            orig, para = s[field], paraphrases[s["id"]][field]
            share = bigram_share(orig, para)
            kept = option_labels(orig) <= option_labels(para)
            rows.append(
                {
                    "scenario_id": s["id"],
                    "field": field,
                    "bigram_share": share,
                    "labels_kept": kept,
                    "passes": kept and share < MAX_SHARE,
                }
            )
    return rows


def gate(narcbench: Path, paraphrase_path: Path) -> dict:
    """Run the check on NARCBench's scenarios; save `gate_p.json` next to the paraphrases."""
    import sys

    sys.path.insert(0, str(narcbench / "generation"))
    sys.path.insert(0, str(narcbench))
    import core

    rows = check(core.SCENARIOS, json.loads(paraphrase_path.read_text()))
    shares = sorted(r["bigram_share"] for r in rows)
    summary = {
        "fields": len(rows),
        "pass": sum(r["passes"] for r in rows),
        "labels_lost": [f"{r['scenario_id']}:{r['field']}" for r in rows if not r["labels_kept"]],
        "median_bigram_share": shares[len(shares) // 2],
        "max_bigram_share": shares[-1],
        "failing": [f"{r['scenario_id']}:{r['field']}" for r in rows if not r["passes"]],
    }
    (paraphrase_path.parent / "gate_p.json").write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=1)
    )
    return summary
