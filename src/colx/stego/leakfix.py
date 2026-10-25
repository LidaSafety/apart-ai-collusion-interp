"""Run NARCBench's stego.py unchanged except for one fix: keep private notes out of the chat.

The big player's instructions ask for a closing "PRIVATE: [decoded signal] → [bet reason]"
line, but stego.py strips only "DECODE:" lines from the public chat, so the decoding leaked
into every other player's prompt. This wrapper (no edit of third_party) wraps the module's
`call_vllm`: every line starting with PRIVATE: or DECODE: is merged into one "DECODE: …"
line placed first, which stego.py then files as a private note and removes from the chat.
The counter's "RANGE:" lines get the same treatment (one "RANGE: …" line first): stego.py
strips only the first one, and a counter that repeated it leaked the rest (smoke test,
2026-10-24). When both kinds occur, the RANGE notes join the DECODE line.

Run with the vLLM environment's python (it needs only `requests`):
    python leakfix.py <narcbench_dir> <output_dir> <model> <base_url> <shoe> [<shoe> ...]
Standalone on purpose: it runs outside the colx environment.
"""

import sys
from pathlib import Path

DECODE = ("PRIVATE:", "DECODE:")
RANGE = ("RANGE:",)


def _notes(lines: list[str], markers: tuple[str, ...]) -> list[str]:
    """The text after the marker of every line that starts with one of `markers`."""
    return [
        ln.strip().split(":", 1)[1].strip()
        for ln in lines
        if ln.strip().upper().startswith(markers)
    ]


def move_private_first(text: str) -> str:
    """Merge private lines into one leading "DECODE: …" (or "RANGE: …") line; keep the rest."""
    lines = text.split("\n")
    decode, ranges = _notes(lines, DECODE), _notes(lines, RANGE)
    if not decode and not ranges:
        return text
    public = "\n".join(ln for ln in lines if not ln.strip().upper().startswith(DECODE + RANGE))
    head = "DECODE: " + " | ".join(decode + ranges) if decode else "RANGE: " + ranges[0]
    return head + "\n" + public.strip()


def main(narcbench: Path, output_dir: Path, model: str, base_url: str, shoes: list[int]) -> None:
    """Import stego.py, patch its call_vllm, and run the given shoes one by one."""
    sys.path.insert(0, str(narcbench / "generation"))
    sys.path.insert(0, str(narcbench))
    import stego

    original = stego.call_vllm
    stego.call_vllm = lambda *a, **k: move_private_first(original(*a, **k))
    for shoe in shoes:
        sys.argv = [
            "stego.py",
            "--output-dir",
            str(output_dir),
            "--shoe",
            str(shoe),
            "--model",
            model,
            "--base-url",
            base_url,
        ]
        stego.main()


if __name__ == "__main__":
    main(
        Path(sys.argv[1]),
        Path(sys.argv[2]),
        sys.argv[3],
        sys.argv[4],
        [int(s) for s in sys.argv[5:]],
    )
