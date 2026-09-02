"""Files the harness and the stubs pass data through.

The stubs run as their own processes, so each file below is one channel between
a test and a stub. An environment variable holds the path of each, and the types
here own what goes inside, so neither side has to know the other's format.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

# Written by the harness before the run, read by the stub during it
EDITOR_PROMPTS_ENV = "LM_TEST_EDITOR_PROMPTS"
CLAUDE_SCRIPT_ENV = "LM_TEST_CLAUDE_SCRIPT"
FZF_MATCH_ENV = "LM_TEST_FZF_MATCH"

# Written by the stub during the run, read by the harness after it
EDITOR_BUFFER_ENV = "LM_TEST_EDITOR_BUFFER"
EDITOR_ARGV_ENV = "LM_TEST_EDITOR_ARGV"
CLAUDE_ARGV_ENV = "LM_TEST_CLAUDE_ARGV"
CLAUDE_STDIN_ENV = "LM_TEST_CLAUDE_STDIN"

STUB_FILE_ENVS = (
    EDITOR_PROMPTS_ENV,
    CLAUDE_SCRIPT_ENV,
    FZF_MATCH_ENV,
    EDITOR_BUFFER_ENV,
    EDITOR_ARGV_ENV,
    CLAUDE_ARGV_ENV,
    CLAUDE_STDIN_ENV,
)

# --- what the claude stub does for one run ---


@dataclass(frozen=True)
class ClaudeSuccess:
    """End the turn as a run that worked."""


@dataclass(frozen=True)
class ClaudeError:
    """End the turn as a run that failed this way."""

    subtype: str
    errors: list[str]


# A run that ends with neither stops without reporting a result at all
ClaudeEnding = ClaudeSuccess | ClaudeError | None


@dataclass(frozen=True)
class ClaudeScript:
    """One scripted claude run: stream this text, then end the turn this way."""

    text: str
    ending: ClaudeEnding

    def to_json(self) -> str:
        ending: dict[str, object] | None
        match self.ending:
            case ClaudeSuccess():
                ending = {"kind": "success"}
            case ClaudeError(subtype=subtype, errors=errors):
                ending = {"kind": "error", "subtype": subtype, "errors": errors}
            case None:
                ending = None
        return json.dumps({"text": self.text, "ending": ending})

    @staticmethod
    def from_json(text: str) -> ClaudeScript:
        script = json.loads(text)
        ending: ClaudeEnding
        match script["ending"]:
            case {"kind": "success"}:
                ending = ClaudeSuccess()
            case {"kind": "error", "subtype": subtype, "errors": errors}:
                ending = ClaudeError(subtype=subtype, errors=errors)
            case None:
                ending = None
        return ClaudeScript(text=script["text"], ending=ending)


# --- what the claude stub records in a session file ---


@dataclass(frozen=True)
class SessionTurn:
    """One turn, as the claude stub records it in a session file."""

    prompt: str

    def to_line(self) -> str:
        return json.dumps({"prompt": self.prompt}) + "\n"

    @staticmethod
    def from_line(line: str) -> SessionTurn:
        return SessionTurn(prompt=json.loads(line)["prompt"])


# --- what the editor stubs type into the buffer ---


_PROMPT_SEPARATOR = "\n<!-- next prompt -->\n"


@dataclass(frozen=True)
class PromptQueue:
    """The prompts an editor stub types, one per run, in the order it takes them."""

    prompts: list[str]

    def to_text(self) -> str:
        return _PROMPT_SEPARATOR.join(self.prompts)

    @staticmethod
    def from_text(text: str) -> PromptQueue:
        return PromptQueue(prompts=text.split(_PROMPT_SEPARATOR))
