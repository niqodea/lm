"""Sandbox for driving the lm CLI end to end."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
from .stubs import protocol

LM_PATH = Path(__file__).parent / "lm"
STUBS_PATH = Path(__file__).parent / "stubs"

RUN_TIMEOUT_SECONDS = 30.0


class Lm:
    """The lm CLI, wired to stub tools instead of a terminal and a real Claude."""

    def __init__(self, root_path: Path, env: dict[str, str]) -> None:
        self._root_path = root_path
        self._env = env

    @staticmethod
    def create(root_path: Path) -> Lm:
        bin_path = root_path / "bin"
        bin_path.mkdir()
        # lm looks these up on PATH, and reads the editor's name off EDITOR.
        # These are symlinks, not copies, so the stubs still find protocol.py
        # next to their real selves.
        (bin_path / "claude").symlink_to(STUBS_PATH / "claude")
        (bin_path / "fzf").symlink_to(STUBS_PATH / "fzf")
        (bin_path / "nano").symlink_to(STUBS_PATH / "nano")
        (bin_path / "vim").symlink_to(STUBS_PATH / "vim")

        (root_path / "home").mkdir()
        (root_path / "config").mkdir()
        # LM_TTY is opened, never created
        (root_path / "tty").touch()
        # Each stub file is named after the variable that carries its path
        for name in protocol.STUB_FILE_ENVS:
            (root_path / name).touch()

        env = {
            **os.environ,
            "PATH": f"{bin_path}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(root_path / "home"),
            "XDG_CONFIG_HOME": str(root_path / "config"),
            "LM_DATA_DIR": str(root_path / "data"),
            "LM_TTY": str(root_path / "tty"),
            "EDITOR": str(bin_path / "nano"),
            **{name: str(root_path / name) for name in protocol.STUB_FILE_ENVS},
        }

        lm = Lm(root_path, env)
        # Every run needs a script, so a test that ignores claude still has one.
        lm.set_claude_result_success("")
        lm.invoke("init", stdin="")
        return lm

    def invoke(self, *args: str, stdin: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603
            [str(LM_PATH), *args],
            env=self._env,
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
            timeout=RUN_TIMEOUT_SECONDS,
        )

    def set_editor(self, name: str) -> None:
        self._env["EDITOR"] = str(self._root_path / "bin" / name)

    def set_editor_prompt(self, prompt: str) -> None:
        self.set_editor_prompts(prompt)

    def set_editor_prompts(self, *prompts: str) -> None:
        """Queue one prompt per editor run, so a chat loop ends when they run out."""
        queued = protocol.PromptQueue(prompts=list(prompts)).to_text()
        self._get_stub_file_path(protocol.EDITOR_PROMPTS_ENV).write_text(queued)

    def set_claude_result_success(self, text: str) -> None:
        """Make the claude stub stream the text, then end the turn successfully."""
        self._set_claude_run([protocol.ClaudeText(text=text)], protocol.ClaudeSuccess())

    def set_claude_result_success_with_tool_calls(
        self,
        text_before: str,
        tool_calls: list[tuple[str, dict[str, object]]],
        text: str,
    ) -> None:
        """Make the claude stub call these (name, arguments) tools mid-response."""
        self._set_claude_run(
            [
                protocol.ClaudeText(text=text_before),
                *[
                    protocol.ClaudeToolCall(name=name, arguments=arguments)
                    for name, arguments in tool_calls
                ],
                protocol.ClaudeText(text=text),
            ],
            protocol.ClaudeSuccess(),
        )

    def set_claude_result_success_with_compaction(
        self, text_before: str, pre_tokens: int, text: str
    ) -> None:
        """Make the claude stub compact part way through the response."""
        self._set_claude_run(
            [
                protocol.ClaudeText(text=text_before),
                protocol.ClaudeCompaction(pre_tokens=pre_tokens),
                protocol.ClaudeText(text=text),
            ],
            protocol.ClaudeSuccess(),
        )

    def set_claude_result_error(
        self, text: str, subtype: str, errors: list[str]
    ) -> None:
        """Make the claude stub stream the text, then end the turn with an error."""
        self._set_claude_run(
            [protocol.ClaudeText(text=text)],
            protocol.ClaudeError(subtype=subtype, errors=errors),
        )

    def set_claude_result_absent(self, text: str) -> None:
        """Make the claude stub stream the text, then stop without a result."""
        self._set_claude_run([protocol.ClaudeText(text=text)], None)

    def set_selected_thread(self, name: str) -> None:
        self._get_stub_file_path(protocol.FZF_MATCH_ENV).write_text(name)

    def set_preset(self, name: str, body: str) -> None:
        presets_path = self._root_path / "config" / "lm" / "presets"
        (presets_path / f"{name}.md").write_text(body)

    def get_editor_buffer(self) -> str:
        """Return the buffer lm handed the editor, before it was edited."""
        return self._get_stub_file_path(protocol.EDITOR_BUFFER_ENV).read_text()

    def get_editor_argv(self) -> list[str]:
        return self._get_json(protocol.EDITOR_ARGV_ENV)

    def get_claude_argv(self) -> list[str]:
        return self._get_json(protocol.CLAUDE_ARGV_ENV)

    def get_claude_prompt(self) -> str:
        return self.get_claude_argv()[0]

    def get_claude_stdin(self) -> str:
        return self._get_stub_file_path(protocol.CLAUDE_STDIN_ENV).read_text()

    def get_session_prompts(self, thread: str) -> list[str]:
        """Return the prompts recorded in the session claude has been resuming."""
        session_path = self.get_thread_path(thread) / ".claude" / "session.jsonl"
        lines = session_path.read_text().splitlines()
        return [protocol.SessionTurn.from_line(line).prompt for line in lines]

    def get_thread_path(self, thread: str) -> Path:
        return self._root_path / "data" / "threads" / thread

    def get_staged_path(self, thread: str) -> Path:
        return self.get_thread_path(thread) / "STAGED"

    def get_turn_path(self, thread: str, turn_idx: int) -> Path:
        return sorted(self.get_thread_path(thread).glob("[0-9]*"))[turn_idx]

    def _set_claude_run(
        self, events: list[protocol.ClaudeEvent], ending: protocol.ClaudeEnding
    ) -> None:
        script = protocol.ClaudeScript(events=events, ending=ending)
        path = self._get_stub_file_path(protocol.CLAUDE_SCRIPT_ENV)
        path.write_text(script.to_json())

    def _get_json(self, name: str) -> list[str]:
        loaded: list[str] = json.loads(self._get_stub_file_path(name).read_text())
        return loaded

    def _get_stub_file_path(self, name: str) -> Path:
        return Path(self._env[name])


@pytest.fixture
def lm(tmp_path: Path) -> Lm:
    return Lm.create(tmp_path)
