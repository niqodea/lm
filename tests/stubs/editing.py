"""What both editor stubs do the same way, whichever half they write into."""

import json
import os
from pathlib import Path

from protocol import (
    EDITOR_ARGV_ENV,
    EDITOR_BUFFER_ENV,
    EDITOR_PROMPTS_ENV,
    PromptQueue,
)

# Mirrors lm's own buffer format
SCISSORS_SEPARATOR = "\n<!-- ------------------------ >8 ------------------------ -->\n"


def record_call(buffer: str, argv: list[str]) -> None:
    """Hand the buffer lm built, and how it asked for it, back to the test."""
    Path(os.environ[EDITOR_BUFFER_ENV]).write_text(buffer)
    Path(os.environ[EDITOR_ARGV_ENV]).write_text(json.dumps(argv))


def take_prompt() -> str:
    """Return the next queued prompt, leaving the rest for later runs."""
    prompts_path = Path(os.environ[EDITOR_PROMPTS_ENV])
    queue = PromptQueue.from_text(prompts_path.read_text())
    prompts_path.write_text(PromptQueue(queue.prompts[1:]).to_text())
    return queue.prompts[0]
