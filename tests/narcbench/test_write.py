from pathlib import Path

import pandas as pd
import pytest

from colx.narcbench.write import write_label_tables

REAL_CORE = Path("third_party/narcbench/data/raw/qwen3_32b/core")

# The counts the plan's handoff notes assert (checked on 2026-10-22). One differs from the
# plan's wording: 10 replies write the vote as "[Option A]" or "**Option A**", so 390 (not
# 400) start with "RECOMMENDATION: Option"; all 400 start with "RECOMMENDATION:" and parse.
EXPECTED = {
    "runs_colluded": 32,
    "runs_not_colluded": 68,
    "collusion_runs_2_voted": 32,
    "collusion_runs_1_voted": 9,
    "collusion_runs_0_voted": 9,
    "colluders_voted_target": 73,
    "honest_in_collusion_runs_voted_target": 9,
    "control_agents_voted_target": 0,
    "colluders_not_voted_target": 27,
    "honest_not_voted_target_in_collusion_runs": 91,
    "colluders_standard": 60,
    "colluders_standard_voted": 48,
    "colluders_lowkey": 40,
    "colluders_lowkey_voted": 25,
    "collusion_runs_with_2_private_messages": 50,
    "votes_parsed_and_match": 400,
    "replies_start_recommendation": 400,
    "replies_start_recommendation_option": 390,
    "style_groups": 9,
    "runs_in_groups_with_both_labels": 48,
    "split_runs": 9,
    "same_style": 5,
    "voter_standard_other_lowkey": 4,
    "runs_with_constant_system_prompts": 100,
}


def test_write_label_tables(core_dir: Path, tmp_path: Path) -> None:
    out = tmp_path / "out"
    counts = write_label_tables(core_dir, out)
    assert counts["runs"] == 2
    assert len(pd.read_parquet(out / "agents.parquet")) == 8
    assert (out / "runs.parquet.meta.json").exists()


@pytest.mark.slow
@pytest.mark.gpu
@pytest.mark.skipif(not REAL_CORE.exists(), reason="NARCBench transcripts not present")
def test_real_label_counts(tmp_path: Path) -> None:
    counts = write_label_tables(REAL_CORE, tmp_path)
    assert {k: counts[k] for k in EXPECTED} == EXPECTED
