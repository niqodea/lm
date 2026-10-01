"""Sandbox for driving the lm CLI end to end."""

import json
import os
import subprocess
from pathlib import Path

import pytest
from .stubs import protocol

LM_PATH = Path(__file__).parent / "lm"
STUBS_PATH = Path(__file__).parent / "stubs"

# A run takes well under a second, so this only stops a hung stub from stalling
# the suite
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
        return subprocess.run(  # noqa: S603  (the command is the lm under test)
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
        self.set_editor_prompts([prompt])

    def set_editor_prompts(self, prompts: list[str]) -> None:
        """Queue one prompt per editor run, so a chat loop ends when they run out."""
        queued = protocol.PromptQueue(prompts=tuple(prompts)).to_text()
        self._get_stub_file_path(protocol.EDITOR_PROMPTS_ENV).write_text(queued)

    def set_claude_result_success(self, text: str) -> None:
        """Make the claude stub stream the text, then end the turn successfully."""
        self._set_claude_run(
            (protocol.ClaudeText(text=text),), protocol.ClaudeSuccess()
        )

    def set_claude_result_success_without_session(self, text: str) -> None:
        """Make the claude stub answer, but leave the session untouched."""
        self._set_claude_run(
            (protocol.ClaudeText(text=text),), protocol.ClaudeSuccessWithoutSession()
        )

    def set_claude_result_success_with_tool_calls(
        self,
        text_before: str,
        tool_calls: list[protocol.ClaudeToolCall],
        text: str,
    ) -> None:
        """Make the claude stub call these tools mid-response."""
        self._set_claude_run(
            (
                protocol.ClaudeText(text=text_before),
                *tool_calls,
                protocol.ClaudeText(text=text),
            ),
            protocol.ClaudeSuccess(),
        )

    def set_claude_result_success_with_compaction(
        self, text_before: str, pre_tokens: int, text: str
    ) -> None:
        """Make the claude stub compact part way through the response."""
        self._set_claude_run(
            (
                protocol.ClaudeText(text=text_before),
                protocol.ClaudeCompaction(pre_tokens=pre_tokens),
                protocol.ClaudeText(text=text),
            ),
            protocol.ClaudeSuccess(),
        )

    def set_claude_result_success_after_raw_line(self, line: str, text: str) -> None:
        """Make the claude stub print this line as it is, then answer normally."""
        self._set_claude_run(
            (protocol.ClaudeRawLine(line=line), protocol.ClaudeText(text=text)),
            protocol.ClaudeSuccess(),
        )

    def set_claude_result_raw_line(self, line: str) -> None:
        """Make the claude stub end the turn with this line, as it is."""
        self._set_claude_run((protocol.ClaudeRawLine(line=line),), None)

    def set_claude_result_error(
        self, text: str, subtype: str, errors: list[str]
    ) -> None:
        """Make the claude stub stream the text, then end the turn with an error."""
        self._set_claude_run(
            (protocol.ClaudeText(text=text),),
            protocol.ClaudeError(subtype=subtype, errors=tuple(errors)),
        )

    def set_claude_result_absent(self, text: str) -> None:
        """Make the claude stub stream the text, then stop without a result."""
        self._set_claude_run((protocol.ClaudeText(text=text),), None)

    def set_selected_thread(self, name: str) -> None:
        self._get_stub_file_path(protocol.FZF_MATCH_ENV).write_text(name)

    def set_settings(self, text: str) -> None:
        settings_path = self._root_path / "config" / "lm" / "settings.toml"
        settings_path.write_text(text)

    def set_preset(self, name: str, body: str) -> None:
        presets_path = self._root_path / "config" / "lm" / "presets"
        (presets_path / f"{name}.md").write_text(body)

    def set_default_system_prompt(self, body: str) -> None:
        config_path = self._root_path / "config" / "lm"
        (config_path / "default-system-prompt.md").write_text(body)

    def set_system_prompt(self, name: str, body: str) -> None:
        system_prompts_path = self._root_path / "config" / "lm" / "system-prompts"
        (system_prompts_path / f"{name}.md").write_text(body)

    def get_editor_buffer(self) -> str:
        """Return the buffer lm handed the editor, before it was edited."""
        return self._get_stub_file_path(protocol.EDITOR_BUFFER_ENV).read_text()

    def get_editor_argv(self) -> list[str]:
        return self._get_json(protocol.EDITOR_ARGV_ENV)

    def get_claude_argv(self) -> list[str]:
        return self._get_json(protocol.CLAUDE_ARGV_ENV)

    def get_claude_prompt(self) -> str:
        argv = self.get_claude_argv()
        return argv[argv.index("--") + 1]

    def get_claude_stdin(self) -> str:
        return self._get_stub_file_path(protocol.CLAUDE_STDIN_ENV).read_text()

    def get_claude_session_prompts(self) -> list[str]:
        """Return every prompt in the session of the last claude call, its own last."""
        return self._get_json(protocol.CLAUDE_SESSION_ENV)

    def get_claude_projects_path(self) -> Path:
        """Where claude keeps the session files lm moves into its threads."""
        return self._root_path / "home" / ".claude" / "projects"

    def get_thread_path(self, thread: str) -> Path:
        return self._root_path / "data" / "threads" / thread

    def get_turn_path(self, thread: str, turn_idx: int) -> Path:
        return sorted(self.get_thread_path(thread).glob("[0-9]*"))[turn_idx]

    def _set_claude_run(
        self, events: tuple[protocol.ClaudeEvent, ...], ending: protocol.ClaudeEnding
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
