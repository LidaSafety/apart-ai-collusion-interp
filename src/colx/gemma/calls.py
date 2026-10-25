"""Every agent call of a NARCBench run, with the reply it produced.

`agent_prompts.json` logs each call's system and user prompt in order; the replies live in
`results.json`: private and public messages as "[name]: reply", finals by agent name. The
n-th private/public message of an agent is its reply to its n-th private/discussion call.
"""

import json
from pathlib import Path


def strip_name(message: str, name: str) -> str:
    """The reply text of a logged "[name]: reply" message."""
    prefix = f"[{name}]: "
    if not message.startswith(prefix):
        raise ValueError(f"message does not start with {prefix!r}")
    return message[len(prefix) :]


def run_calls(prompts: list[dict], results: dict) -> list[dict]:
    """One record per call: agent, phase, round, system and user prompt, and the reply."""
    seen: dict[tuple[str, str], int] = {}
    out = []
    for call in prompts:
        name, phase = call["agent_name"], call["phase"]
        k = seen.get((name, phase), 0)
        seen[(name, phase)] = k + 1
        if phase == "final":
            reply = results["final_texts"][name]
        else:
            pool = results["private_messages" if phase == "private" else "public_messages"]
            own = [m for m in pool if m.startswith(f"[{name}]: ")]
            reply = strip_name(own[k], name)
        out.append(
            {
                "agent": name,
                "role": call["role"],
                "phase": phase,
                "round": int(call["round"]),
                "system": call["system_prompt"],
                "user": call["user_prompt"],
                "reply": reply,
            }
        )
    return out


def load_calls(run_dir: Path) -> list[dict]:
    """All calls of one run folder, with the run id attached."""
    prompts = json.loads((run_dir / "agent_prompts.json").read_text())
    results = json.loads((run_dir / "results.json").read_text())
    return [{"run_id": run_dir.name} | c for c in run_calls(prompts, results)]
