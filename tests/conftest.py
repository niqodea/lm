"""Sandbox for driving the lm CLI end to end."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from .stubs import protocol

LM_PATH = Path(__file__).parent.parent / "lm"
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
        # lm looks "claude" up on PATH, and reads the editor's name off EDITOR.
        # These are symlinks, not copies, so the stubs still find protocol.py
        # next to their real selves.
        (bin_path / "claude").symlink_to(STUBS_PATH / "claude")
        (bin_path / "editor").symlink_to(STUBS_PATH / "editor")
        (bin_path / "vim").symlink_to(STUBS_PATH / "editor")

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
            "EDITOR": str(bin_path / "editor"),
            **{name: str(root_path / name) for name in protocol.STUB_FILE_ENVS},
        }

        lm = Lm(root_path, env)
        lm.run("init", stdin="")
        return lm

    def run(self, *args: str, stdin: str) -> subprocess.CompletedProcess[str]:
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
        self._get_stub_file_path(protocol.EDITOR_PROMPT_ENV).write_text(prompt)

    def set_claude_response(self, response: str) -> None:
        self._get_stub_file_path(protocol.CLAUDE_RESPONSE_ENV).write_text(response)

    def get_editor_buffer(self) -> str:
        return self._get_stub_file_path(protocol.EDITOR_BUFFER_ENV).read_text()

    def get_editor_argv(self) -> list[str]:
        return self._get_stub_file_path(protocol.EDITOR_ARGV_ENV).read_text().splitlines()

    def get_claude_argv(self) -> list[str]:
        return self._get_stub_file_path(protocol.CLAUDE_ARGV_ENV).read_text().splitlines()

    def get_claude_stdin(self) -> str:
        return self._get_stub_file_path(protocol.CLAUDE_STDIN_ENV).read_text()

    def get_thread_path(self, thread: str) -> Path:
        return self._root_path / "data" / "threads" / thread

    def get_turn_path(self, thread: str, turn_idx: int) -> Path:
        return sorted(self.get_thread_path(thread).glob("[0-9]*"))[turn_idx]

    def _get_stub_file_path(self, name: str) -> Path:
        return Path(self._env[name])


@pytest.fixture
def lm(tmp_path: Path) -> Lm:
    return Lm.create(tmp_path)
