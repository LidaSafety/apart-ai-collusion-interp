"""A small synthetic agent-score table shaped like `analysis.data.agent_scores`."""

import numpy as np
import pandas as pd
import pytest


def make_table(judge: str = "lens", arm: str = "raw", position: str = "P1", seed: int = 0):
    """6 scenarios x (collusion, control) x 4 agents; colluders who vote the target score high."""
    rng = np.random.default_rng(seed)
    rows = []
    for s in range(6):
        for mode in ("collusion", "control"):
            voted = [True, s % 3 != 0] if mode == "collusion" else [False, False]
            for i in range(4):
                colluder = mode == "collusion" and i < 2
                vt = colluder and voted[i]
                score = (0.8 if vt else 0.2) + rng.normal(scale=0.05)
                rows.append({
                    "judge": judge, "arm": arm, "position": position,
                    "run_id": f"s{s}_{mode}", "agent_index": i, "scenario_id": f"s{s}",
                    "mode": mode, "role": "colluder" if colluder else "honest",
                    "style": "standard", "voted_target": vt, "colluded": vt,
                    "style_group": f"g{s % 2}" if mode == "collusion" else None,
                    "run_colluded": mode == "collusion" and all(voted),
                    "score_A": score, "score_B": score, "score_C": score,
                })  # fmt: skip
    return pd.DataFrame(rows)


@pytest.fixture
def table() -> pd.DataFrame:
    return make_table()
