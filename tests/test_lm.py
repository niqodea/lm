"""End-to-end tests driving the lm CLI as a user would.

Ordered from the plainest intended usage down to the corners: the core loop
first, then the documented workflows, then refusals and details.
"""

from __future__ import annotations

from pathlib import Path

from .conftest import Lm

# --- The core loop ---


def test_new_creates_a_thread(lm: Lm) -> None:
    result = lm.run("new", "demo", stdin="")

    assert result.returncode == 0
    assert lm.get_thread_path("demo").is_dir()


def test_run_saves_the_prompt_and_the_response(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.run("new", "demo", stdin="")
    result = lm.run("run", "--thread", "demo", stdin="")

    assert result.returncode == 0
    turn_path = lm.get_turn_path("demo", 0)
    assert (turn_path / "prompt.md").read_text() == "what is 2+2?\n"
    assert (turn_path / "response.md").read_text() == "4\n"


def test_run_sends_the_prompt_to_claude(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.run("new", "demo", stdin="")
    lm.run("run", "--thread", "demo", stdin="")

    assert "what is 2+2?" in lm.get_claude_argv()


def test_run_prints_the_response(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.run("new", "demo", stdin="")
    result = lm.run("run", "--thread", "demo", stdin="")

    assert "4" in result.stdout


def test_ls_lists_the_thread(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.run("new", "demo", stdin="")
    lm.run("run", "--thread", "demo", stdin="")
    result = lm.run("ls", stdin="")

    assert "demo" in result.stdout
    assert "what is 2+2?" in result.stdout
    assert "4" in result.stdout


def test_show_prints_the_exchange(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.run("new", "demo", stdin="")
    lm.run("run", "--thread", "demo", stdin="")
    result = lm.run("show", "--thread", "demo", stdin="")

    assert "what is 2+2?" in result.stdout
    assert "4" in result.stdout


# --- Managing threads ---


def test_run_without_a_thread_creates_one(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    result = lm.run("run", stdin="")

    assert result.returncode == 0
    assert "what is 2+2?" in lm.run("ls", stdin="").stdout


def test_mv_renames_a_thread(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.run("new", "before", stdin="")
    lm.run("run", "--thread", "before", stdin="")
    result = lm.run("mv", "before", "after", stdin="")

    assert result.returncode == 0
    assert not lm.get_thread_path("before").exists()
    assert (lm.get_turn_path("after", 0) / "prompt.md").read_text() == "what is 2+2?\n"


def test_rm_deletes_a_thread(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.run("new", "demo", stdin="")
    lm.run("run", "--thread", "demo", stdin="")
    result = lm.run("rm", "demo", stdin="")

    assert result.returncode == 0
    assert not lm.get_thread_path("demo").exists()


def test_last_resumes_the_most_recent_thread(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.run("new", "older", stdin="")
    lm.run("new", "newer", stdin="")
    result = lm.run("run", "--last", stdin="")

    assert result.returncode == 0
    assert (lm.get_turn_path("newer", 0) / "prompt.md").read_text() == "what is 2+2?\n"


# --- Feeding context in ---


def test_piped_stdin_reaches_claude(lm: Lm) -> None:
    lm.set_editor_prompt("summarize this\n")
    lm.set_claude_response("done")

    lm.run("new", "demo", stdin="")
    lm.run("run", "--thread", "demo", stdin="PIPED CONTEXT")

    assert lm.get_claude_stdin() == "PIPED CONTEXT"


def test_piped_stdin_is_saved_with_the_turn(lm: Lm) -> None:
    lm.set_editor_prompt("summarize this\n")
    lm.set_claude_response("done")

    lm.run("new", "demo", stdin="")
    lm.run("run", "--thread", "demo", stdin="PIPED CONTEXT")

    assert (lm.get_turn_path("demo", 0) / "stdin").read_text() == "PIPED CONTEXT"


def test_piped_stdin_does_not_reach_the_editor(lm: Lm) -> None:
    lm.set_editor_prompt("summarize this\n")
    lm.set_claude_response("done")

    lm.run("new", "demo", stdin="")
    lm.run("run", "--thread", "demo", stdin="PIPED CONTEXT")

    # The editor is handed the terminal, never the pipe lm was given
    assert "PIPED CONTEXT" not in lm.get_editor_buffer()


def test_attachment_is_saved_with_the_turn(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("read this\n")
    lm.set_claude_response("read it")
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("ATTACHED TEXT")

    lm.run("new", "demo", stdin="")
    lm.run("run", "--thread", "demo", "--attach", str(attachment_path), stdin="")

    saved_path = lm.get_turn_path("demo", 0) / "attachments" / "notes.md"
    assert saved_path.read_text() == "ATTACHED TEXT"


def test_attachment_is_announced_to_claude(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("read this\n")
    lm.set_claude_response("read it")
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("ATTACHED TEXT")

    lm.run("new", "demo", stdin="")
    lm.run("run", "--thread", "demo", "--attach", str(attachment_path), stdin="")

    assert "- @notes.md" in lm.get_claude_argv()


def test_attachment_alias_renames_the_saved_file(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("read this\n")
    lm.set_claude_response("read it")
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("ATTACHED TEXT")

    lm.run("new", "demo", stdin="")
    lm.run("run", "--thread", "demo", "--attach", f"{attachment_path}:renamed.md", stdin="")

    attachments_path = lm.get_turn_path("demo", 0) / "attachments"
    assert (attachments_path / "renamed.md").read_text() == "ATTACHED TEXT"
    assert not (attachments_path / "notes.md").exists()


# --- Several turns ---


def test_second_run_starts_a_second_turn(lm: Lm) -> None:
    lm.set_claude_response("an answer")

    lm.run("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.run("run", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.run("run", "--thread", "demo", stdin="")

    assert (lm.get_turn_path("demo", 0) / "prompt.md").read_text() == "first question\n"
    assert (lm.get_turn_path("demo", 1) / "prompt.md").read_text() == "second question\n"


def test_past_turns_appear_in_the_editor(lm: Lm) -> None:
    lm.set_claude_response("first answer")

    lm.run("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.run("run", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.run("run", "--thread", "demo", stdin="")

    buffer = lm.get_editor_buffer()
    assert "first question" in buffer
    assert "first answer" in buffer


def test_past_turns_are_not_resent_to_claude(lm: Lm) -> None:
    lm.set_claude_response("first answer")

    lm.run("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.run("run", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.run("run", "--thread", "demo", stdin="")

    # The session carries the history, so only the new prompt is sent
    assert "first question" not in lm.get_claude_argv()


# --- The staged workflow ---


def test_edit_prompt_stages_a_prompt(lm: Lm) -> None:
    lm.set_editor_prompt("staged question\n")

    lm.run("new", "demo", stdin="")
    result = lm.run("edit-prompt", "--thread", "demo", stdin="")

    assert result.returncode == 0
    staged_path = lm.get_thread_path("demo") / "STAGED"
    assert (staged_path / "prompt.md").read_text() == "staged question\n"


def test_attach_adds_to_the_staged_query(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("staged question\n")
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("ATTACHED TEXT")

    lm.run("new", "demo", stdin="")
    lm.run("edit-prompt", "--thread", "demo", stdin="")
    result = lm.run("attach", "--thread", "demo", str(attachment_path), stdin="")

    assert result.returncode == 0
    staged_path = lm.get_thread_path("demo") / "STAGED"
    assert (staged_path / "attachments" / "notes.md").read_text() == "ATTACHED TEXT"


def test_commit_turns_the_staged_query_into_a_turn(lm: Lm) -> None:
    lm.set_editor_prompt("staged question\n")
    lm.set_claude_response("staged answer")

    lm.run("new", "demo", stdin="")
    lm.run("edit-prompt", "--thread", "demo", stdin="")
    result = lm.run("commit", "--thread", "demo", stdin="")

    assert result.returncode == 0
    assert not (lm.get_thread_path("demo") / "STAGED").exists()
    turn_path = lm.get_turn_path("demo", 0)
    assert (turn_path / "prompt.md").read_text() == "staged question\n"
    assert (turn_path / "response.md").read_text() == "staged answer\n"


def test_clear_discards_the_staged_query(lm: Lm) -> None:
    lm.set_editor_prompt("staged question\n")

    lm.run("new", "demo", stdin="")
    lm.run("edit-prompt", "--thread", "demo", stdin="")
    result = lm.run("clear", "--thread", "demo", stdin="")

    assert result.returncode == 0
    assert not (lm.get_thread_path("demo") / "STAGED").exists()
    assert list(lm.get_thread_path("demo").glob("[0-9]*")) == []


# --- Thread settings ---


def test_thread_model_reaches_claude(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_response("hi")

    lm.run("new", "demo", "--claude-model", "claude-haiku-4-5", stdin="")
    lm.run("run", "--thread", "demo", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--model") + 1] == "claude-haiku-4-5"


def test_thread_capability_reaches_claude(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_response("hi")

    lm.run("new", "demo", "--with", "web", stdin="")
    lm.run("run", "--thread", "demo", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--tools") + 1] == "WebFetch,WebSearch"


def test_a_thread_without_capabilities_gets_no_tools(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_response("hi")

    lm.run("new", "demo", stdin="")
    lm.run("run", "--thread", "demo", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--tools") + 1] == ""


# --- Refusals ---


def test_run_refuses_while_a_query_is_staged(lm: Lm) -> None:
    lm.set_editor_prompt("staged question\n")

    lm.run("new", "demo", stdin="")
    lm.run("edit-prompt", "--thread", "demo", stdin="")
    result = lm.run("run", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "Staged query already exists" in result.stderr


def test_an_empty_prompt_creates_no_turn(lm: Lm) -> None:
    lm.set_editor_prompt("")

    lm.run("new", "demo", stdin="")
    result = lm.run("run", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "Prompt is empty" in result.stderr
    assert not list(lm.get_thread_path("demo").glob("[0-9]*"))


def test_mv_refuses_an_existing_destination(lm: Lm) -> None:
    lm.run("new", "before", stdin="")
    lm.run("new", "after", stdin="")
    result = lm.run("mv", "before", "after", stdin="")

    assert result.returncode != 0
    assert "Thread already exists" in result.stderr
    assert lm.get_thread_path("before").is_dir()


def test_rm_refuses_an_unknown_thread(lm: Lm) -> None:
    result = lm.run("rm", "missing", stdin="")

    assert result.returncode != 0
    assert "Thread does not exist" in result.stderr


def test_commit_refuses_without_a_staged_query(lm: Lm) -> None:
    lm.run("new", "demo", stdin="")
    result = lm.run("commit", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "No staged query found" in result.stderr


def test_an_unnamed_thread_is_rejected(lm: Lm) -> None:
    result = lm.run("new", "../escape", stdin="")

    assert result.returncode != 0
    assert "Invalid thread name" in result.stderr


# --- Details of the saved turn ---


def test_committed_turn_files_are_read_only(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.run("new", "demo", stdin="")
    lm.run("run", "--thread", "demo", stdin="")

    turn_path = lm.get_turn_path("demo", 0)
    assert (turn_path / "prompt.md").stat().st_mode & 0o222 == 0
    assert (turn_path / "response.md").stat().st_mode & 0o222 == 0


# --- Editor-specific buffer layout ---


def test_vim_gets_the_prompt_below_the_history(lm: Lm) -> None:
    lm.set_editor("vim")
    lm.set_claude_response("first answer")

    lm.run("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.run("run", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.run("run", "--thread", "demo", stdin="")

    buffer = lm.get_editor_buffer()
    assert buffer.index("first question") < buffer.index("second question")


def test_vim_is_told_to_jump_to_the_prompt(lm: Lm) -> None:
    lm.set_editor("vim")
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.run("new", "demo", stdin="")
    lm.run("run", "--thread", "demo", stdin="")

    assert "+$" in lm.get_editor_argv()


def test_other_editors_get_the_prompt_above_the_history(lm: Lm) -> None:
    lm.set_claude_response("first answer")

    lm.run("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.run("run", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.run("run", "--thread", "demo", stdin="")

    buffer = lm.get_editor_buffer()
    assert buffer.index("second question") < buffer.index("first question")
    assert "+$" not in lm.get_editor_argv()
