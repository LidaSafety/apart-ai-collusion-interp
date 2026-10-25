"""Check stored round-4 activations against a fresh recompute of a few runs (GPU).

For each agent of the checked runs it records:
- whether the stored P1 / P2 token indices equal the ones found in the re-rendered prompt;
- the cosine similarity of stored vs fresh residuals at every block (pass: all ≥ 0.999;
  bf16 never matches bit for bit);
- the block-numbering check: stored block l must be closer to fresh block l than to l ± 1;
- the logit-lens check: the stored last-block residual at P1, unembedded, must predict the
  agent's actual first reply token.
"""

from pathlib import Path

import pandas as pd
import torch
from safetensors.torch import load_file

from colx import provenance, qwen
from colx.extract.recompute import block_outputs, read_positions, tokenize_with_offsets
from colx.narcbench.runs import join_final_prompt
from colx.unembed import Unembed, from_model

MIN_COSINE = 0.999
DEFAULT_RUNS = ("deception__audit_01__collusion", "deception__audit_01__control")


def cosine_per_block(stored: torch.Tensor, fresh: torch.Tensor) -> torch.Tensor:
    """Cosine similarity per block of two [blocks, d] residual stacks, in fp32."""
    return torch.nn.functional.cosine_similarity(stored.float(), fresh.float(), dim=-1)


def blocks_aligned(stored: torch.Tensor, fresh: torch.Tensor) -> int:
    """Count blocks l where stored l is closer to fresh l than to fresh l-1 and l+1."""
    same = cosine_per_block(stored, fresh)
    ok = torch.ones_like(same, dtype=torch.bool)
    ok[1:] &= same[1:] > cosine_per_block(stored[1:], fresh[:-1])
    ok[:-1] &= same[:-1] > cosine_per_block(stored[:-1], fresh[1:])
    return int(ok.sum())


def _agent_row(stored: torch.Tensor, fresh: torch.Tensor, unembed: Unembed) -> dict[str, object]:
    """Compare one agent's stored and fresh [2, blocks, d] residuals."""
    cos = [cosine_per_block(stored[p], fresh[p]) for p in range(2)]
    return {
        "min_cos_p1": cos[0].min().item(),
        "min_cos_p2": cos[1].min().item(),
        "worst_block_p1": int(cos[0].argmin()),
        "worst_block_p2": int(cos[1].argmin()),
        "aligned_blocks_p1": blocks_aligned(stored[0], fresh[0]),
        "aligned_blocks_p2": blocks_aligned(stored[1], fresh[1]),
        "logit_lens_top1": int(unembed(stored[0, -1]).argmax()),
        "cos_p1": cos[0].tolist(),
        "cos_p2": cos[1].tolist(),
    }


def _check_agent(
    tokenizer,
    model,
    unembed: Unembed,
    agent: pd.Series,
    run: pd.Series,
    stored: torch.Tensor,
    with_response: bool,
) -> dict[str, object]:
    """Re-render one agent's final prompt, recompute P1/P2 and compare with `stored`.

    With `with_response`, the forward pass also covers the agent's reply, as the stored
    extraction did; tokens after P1 cannot change P1/P2 in exact arithmetic, but bf16
    kernels can differ with sequence length.
    """
    user = join_final_prompt(run["brief"], run["discussion"], run["request"])
    rendered = qwen.render_chat(tokenizer, agent["system_prompt"], user)
    ids, offsets = tokenize_with_offsets(tokenizer, rendered)
    p1, p2 = read_positions(rendered, run["discussion"], offsets)
    reply = tokenizer(agent["final_text"] + "<|im_end|>\n", add_special_tokens=False)
    forward_ids = ids + reply["input_ids"] if with_response else ids
    fresh = block_outputs(model, forward_ids, [p1, p2])
    return {
        "n_tokens_forward": len(forward_ids),
        "ends_with_empty_think": rendered.endswith(qwen.EMPTY_THINK),
        "n_tokens_fresh": len(ids),
        "p1_fresh": p1,
        "p2_fresh": p2,
        "p1_token_text": tokenizer.decode([ids[p1]]),
        "p2_token_text": tokenizer.decode([ids[p2]]),
        "p2_next_text": tokenizer.decode(ids[p2 + 1 : p2 + 4]),
        "first_reply_token": tokenizer(agent["final_text"], add_special_tokens=False)["input_ids"][
            0
        ],
        **_agent_row(stored, fresh, unembed),
    }


def check_runs(
    model_path: str, out_dir: Path, run_ids: tuple[str, ...], with_response: bool = False
) -> pd.DataFrame:
    """Recompute the final calls of `run_ids` and compare them with the stored residuals."""
    agents = pd.read_parquet(out_dir / "agents.parquet").set_index(["run_id", "agent"])
    runs = pd.read_parquet(out_dir / "runs.parquet").set_index("run_id")
    index = pd.read_parquet(out_dir / "activations_index.parquet")
    stored_all = load_file(str(out_dir / "activations.safetensors"))["resid"]
    tokenizer, model = qwen.load_tokenizer(model_path), qwen.load_model(model_path)
    unembed = from_model(model)
    rows = []
    for i, row in index[index["run_id"].isin(run_ids)].iterrows():
        agent = agents.loc[(row["run_id"], row["agent"])]
        checked = _check_agent(
            tokenizer, model, unembed, agent, runs.loc[row["run_id"]], stored_all[i], with_response
        )
        stored_cols = {
            "n_tokens_stored": int(row["n_tokens"]),
            "p1_stored": int(row["p1_token"]),
            "p2_stored": int(row["p2_token"]),
        }
        rows.append({"run_id": row["run_id"], "agent": row["agent"], **stored_cols, **checked})
    return pd.DataFrame(rows)


def passed(table: pd.DataFrame, n_blocks: int = 64) -> dict[str, bool]:
    """Turn the per-agent check table into the plan's pass/fail verdicts."""
    return {
        "p1_index_matches": bool((table["p1_fresh"] == table["p1_stored"]).all()),
        "p2_index_matches": bool((table["p2_fresh"] == table["p2_stored"]).all()),
        "prompt_ends_with_empty_think": bool(table["ends_with_empty_think"].all()),
        "cosine_at_least_0.999": bool(
            (table[["min_cos_p1", "min_cos_p2"]].min(axis=1) >= MIN_COSINE).all()
        ),
        "block_numbering_aligned": bool(
            (table[["aligned_blocks_p1", "aligned_blocks_p2"]] == n_blocks).all().all()
        ),
        "logit_lens_predicts_reply": bool(
            (table["logit_lens_top1"] == table["first_reply_token"]).all()
        ),
    }


def blocks_below(table: pd.DataFrame) -> dict[str, list[int]]:
    """Per agent and position, the blocks whose cosine is below the threshold."""
    found = {}
    for row in table.itertuples():
        for position in ("p1", "p2"):
            cos = getattr(row, f"cos_{position}")
            found[f"{row.run_id} {row.agent} {position.upper()}"] = [
                b for b, c in enumerate(cos) if c < MIN_COSINE
            ]
    return found


def write_check(
    model_path: str, out_dir: Path, run_ids: tuple[str, ...], with_response: bool = False
) -> tuple[pd.DataFrame, dict]:
    """Run the check, save `activation_check[_with_response].parquet`; return table, verdicts."""
    table = check_runs(model_path, out_dir, run_ids, with_response)
    verdicts = passed(table)
    suffix = "_with_response" if with_response else ""
    path = out_dir / f"activation_check{suffix}.parquet"
    table.to_parquet(path, index=False)
    provenance.write_meta(
        path,
        provenance.collect(
            "col lens-judge check-activations",
            model_path=model_path,
            runs=run_ids,
            with_response=with_response,
            verdicts=verdicts,
        ),
    )
    return table, verdicts
