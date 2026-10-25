import os
from pathlib import Path

import pytest

from colx.qwen import EMPTY_THINK, load_tokenizer, render_chat

# On the pod the model lives in a local snapshot folder; elsewhere set COLX_QWEN_PATH.
QWEN_PATH = Path(os.environ.get("COLX_QWEN_PATH", "/root/hf-local/Qwen3-32B"))


@pytest.mark.slow
@pytest.mark.gpu
@pytest.mark.skipif(not QWEN_PATH.exists(), reason="Qwen3-32B tokenizer not present")
def test_render_chat_ends_with_empty_think_block() -> None:
    tokenizer = load_tokenizer(str(QWEN_PATH))
    rendered = render_chat(tokenizer, "You are Ann.", "Vote now.")
    assert rendered.startswith("<|im_start|>system\nYou are Ann.<|im_end|>")
    assert rendered.endswith("<|im_start|>assistant\n" + EMPTY_THINK)
