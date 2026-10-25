"""Every player's public call in a NARCBench-Stego run, with its reply, role and hand label.

- A player's n-th public message ("[name]: …") is its reply to its n-th discussion call;
  its last hand's reply is in `final_texts`. Pit-boss and private calls are left out.
- Roles: "counter" (told to signal the count), "big_player" (told to read the counter's
  message in the TABLE CHAT and bet on it), "honest". Control runs have only honest players.
- Hand label: the running count's range when the hand's table talk happens (stego.py:
  NEGATIVE < 0, NEUTRAL 0..2, HOT >= 3), from `hand_results` (recorded in both modes).
"""

import json
from pathlib import Path

from colx.gemma.calls import strip_name


def count_range(running_count: int) -> str:
    """stego.py's range of a running count."""
    if running_count < 0:
        return "NEGATIVE"
    return "NEUTRAL" if running_count <= 2 else "HOT"


def player_role(role: str, system: str) -> str:
    """counter, big_player or honest."""
    if role != "colluder":
        return role
    return "big_player" if "TABLE CHAT" in system else "counter"


def stego_calls(prompts: list[dict], results: dict) -> list[dict]:
    """Records of every player's public call: agent, role, hand, label, prompts and reply."""
    ranges = {h["hand"]: count_range(int(h["running_count"])) for h in results["hand_results"]}
    seen: dict[str, int] = {}
    out = []
    for call in prompts:
        if call["role"] == "judge" or call["phase"] == "private":
            continue
        name, hand = call["agent_name"], int(call["round"])
        if call["phase"] == "final":
            reply = results["final_texts"][name]
        else:
            k = seen.get(name, 0)
            seen[name] = k + 1
            own = [m for m in results["public_messages"] if m.startswith(f"[{name}]: ")]
            reply = strip_name(own[k], name)
        out.append(
            {
                "agent": name,
                "role": player_role(call["role"], call["system_prompt"]),
                "hand": hand,
                "label": ranges[hand],
                "system": call["system_prompt"],
                "user": call["user_prompt"],
                "reply": reply,
            }
        )
    return out


def load_stego_calls(run_dir: Path) -> list[dict]:
    """All player calls of one run folder, with the run id and mode attached."""
    prompts = json.loads((run_dir / "agent_prompts.json").read_text())
    results = json.loads((run_dir / "results.json").read_text())
    mode = "collusion" if run_dir.name.endswith("collusion") else "control"
    return [{"run_id": run_dir.name, "mode": mode} | c for c in stego_calls(prompts, results)]
