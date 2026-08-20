"""End-to-end tests driving the lm CLI as a user would.

Ordered from the plainest intended usage down to the corners: the core loop
first, then the documented workflows, then refusals and details.
"""

from __future__ import annotations

from pathlib import Path

from .conftest import Lm

# --- The core loop ---


def test_new_creates_a_thread(lm: Lm) -> None:
    result = lm.invoke("new", "demo", stdin="")

    assert result.returncode == 0
    assert lm.get_thread_path("demo").is_dir()


def test_run_saves_the_prompt_and_the_response(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("run", "--thread", "demo", stdin="")

    assert result.returncode == 0
    turn_path = lm.get_turn_path("demo", 0)
    assert (turn_path / "prompt.md").read_text() == "what is 2+2?\n"
    assert (turn_path / "response.md").read_text() == "4\n"


def test_run_sends_the_prompt_to_claude(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("run", "--thread", "demo", stdin="")

    assert lm.get_claude_prompt() == "what is 2+2?"


def test_run_prints_the_response(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("run", "--thread", "demo", stdin="")

    assert "4" in result.stdout


def test_ls_lists_the_thread(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("run", "--thread", "demo", stdin="")
    result = lm.invoke("ls", stdin="")

    assert "demo" in result.stdout
    assert "what is 2+2?" in result.stdout
    assert "4" in result.stdout


def test_show_prints_the_exchange(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("run", "--thread", "demo", stdin="")
    result = lm.invoke("show", "--thread", "demo", stdin="")

    assert "what is 2+2?" in result.stdout
    assert "4" in result.stdout


# --- Managing threads ---


def test_run_without_a_thread_creates_one(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    result = lm.invoke("run", stdin="")

    assert result.returncode == 0
    assert "what is 2+2?" in lm.invoke("ls", stdin="").stdout


def test_rename_changes_a_thread_name(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.invoke("new", "before", stdin="")
    lm.invoke("run", "--thread", "before", stdin="")
    result = lm.invoke("rename", "--thread", "before", "after", stdin="")

    assert result.returncode == 0
    assert not lm.get_thread_path("before").exists()
    assert (lm.get_turn_path("after", 0) / "prompt.md").read_text() == "what is 2+2?\n"


def test_rm_deletes_a_thread(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("run", "--thread", "demo", stdin="")
    result = lm.invoke("rm", "--thread", "demo", stdin="")

    assert result.returncode == 0
    assert not lm.get_thread_path("demo").exists()


def test_last_resumes_the_most_recent_thread(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.invoke("new", "older", stdin="")
    lm.invoke("new", "newer", stdin="")
    result = lm.invoke("run", "--last", stdin="")

    assert result.returncode == 0
    assert (lm.get_turn_path("newer", 0) / "prompt.md").read_text() == "what is 2+2?\n"


def test_select_picks_a_thread(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.invoke("new", "wanted", stdin="")
    lm.invoke("new", "other", stdin="")
    lm.set_selected_thread("wanted")
    result = lm.invoke("run", "--select", stdin="")

    assert result.returncode == 0
    assert (lm.get_turn_path("wanted", 0) / "prompt.md").read_text() == "what is 2+2?\n"


# --- Feeding context in ---


def test_piped_stdin_reaches_claude(lm: Lm) -> None:
    lm.set_editor_prompt("summarize this\n")
    lm.set_claude_response("done")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("run", "--thread", "demo", stdin="PIPED CONTEXT")

    assert lm.get_claude_stdin() == "PIPED CONTEXT"


def test_piped_stdin_is_saved_with_the_turn(lm: Lm) -> None:
    lm.set_editor_prompt("summarize this\n")
    lm.set_claude_response("done")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("run", "--thread", "demo", stdin="PIPED CONTEXT")

    assert (lm.get_turn_path("demo", 0) / "stdin").read_text() == "PIPED CONTEXT"


def test_piped_stdin_does_not_reach_the_editor(lm: Lm) -> None:
    lm.set_editor_prompt("summarize this\n")
    lm.set_claude_response("done")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("run", "--thread", "demo", stdin="PIPED CONTEXT")

    # The editor is handed the terminal, never the pipe lm was given
    assert "PIPED CONTEXT" not in lm.get_editor_buffer()


def test_attachment_is_saved_with_the_turn(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("read this\n")
    lm.set_claude_response("read it")
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("ATTACHED TEXT")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("run", "--thread", "demo", "--attach", str(attachment_path), stdin="")

    saved_path = lm.get_turn_path("demo", 0) / "attachments" / "notes.md"
    assert saved_path.read_text() == "ATTACHED TEXT"


def test_attachment_is_announced_to_claude(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("read this\n")
    lm.set_claude_response("read it")
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("ATTACHED TEXT")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("run", "--thread", "demo", "--attach", str(attachment_path), stdin="")

    assert "- @notes.md" in lm.get_claude_prompt()


def test_attachment_alias_renames_the_saved_file(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("read this\n")
    lm.set_claude_response("read it")
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("ATTACHED TEXT")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("run", "--thread", "demo", "--attach", f"{attachment_path}:renamed.md", stdin="")

    attachments_path = lm.get_turn_path("demo", 0) / "attachments"
    assert (attachments_path / "renamed.md").read_text() == "ATTACHED TEXT"
    assert not (attachments_path / "notes.md").exists()


def test_a_preset_is_offered_as_a_draft(lm: Lm) -> None:
    lm.set_preset("review", "REVIEW THIS CODE")
    lm.set_editor_prompt("go\n")
    lm.set_claude_response("ok")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("run", "--thread", "demo", "--preset", "review", stdin="")

    assert "REVIEW THIS CODE" in lm.get_editor_buffer()


# --- Several turns ---


def test_second_run_starts_a_second_turn(lm: Lm) -> None:
    lm.set_claude_response("an answer")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.invoke("run", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.invoke("run", "--thread", "demo", stdin="")

    assert (lm.get_turn_path("demo", 0) / "prompt.md").read_text() == "first question\n"
    assert (lm.get_turn_path("demo", 1) / "prompt.md").read_text() == "second question\n"


def test_past_turns_appear_in_the_editor(lm: Lm) -> None:
    lm.set_claude_response("first answer")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.invoke("run", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.invoke("run", "--thread", "demo", stdin="")

    buffer = lm.get_editor_buffer()
    assert "first question" in buffer
    assert "first answer" in buffer


def test_past_turns_are_not_resent_to_claude(lm: Lm) -> None:
    lm.set_claude_response("first answer")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.invoke("run", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.invoke("run", "--thread", "demo", stdin="")

    # The session carries the history, so only the new prompt is sent
    assert "first question" not in lm.get_claude_prompt()


def test_chat_runs_each_queued_prompt_as_a_turn(lm: Lm) -> None:
    lm.set_claude_response("an answer")
    lm.set_editor_prompts("first question\n", "second question\n")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("chat", "--thread", "demo", stdin="")

    assert result.returncode == 0
    assert (lm.get_turn_path("demo", 0) / "prompt.md").read_text() == "first question\n"
    assert (lm.get_turn_path("demo", 1) / "prompt.md").read_text() == "second question\n"


# --- The staged workflow ---


def test_edit_prompt_stages_a_prompt(lm: Lm) -> None:
    lm.set_editor_prompt("staged question\n")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("edit-prompt", "--thread", "demo", stdin="")

    assert result.returncode == 0
    staged_path = lm.get_staged_path("demo")
    assert (staged_path / "prompt.md").read_text() == "staged question\n"


def test_attach_adds_to_the_staged_query(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("staged question\n")
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("ATTACHED TEXT")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("edit-prompt", "--thread", "demo", stdin="")
    result = lm.invoke("attach", "--thread", "demo", str(attachment_path), stdin="")

    assert result.returncode == 0
    staged_path = lm.get_staged_path("demo")
    assert (staged_path / "attachments" / "notes.md").read_text() == "ATTACHED TEXT"


def test_commit_turns_the_staged_query_into_a_turn(lm: Lm) -> None:
    lm.set_editor_prompt("staged question\n")
    lm.set_claude_response("staged answer")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("edit-prompt", "--thread", "demo", stdin="")
    result = lm.invoke("commit", "--thread", "demo", stdin="")

    assert result.returncode == 0
    assert not lm.get_staged_path("demo").exists()
    turn_path = lm.get_turn_path("demo", 0)
    assert (turn_path / "prompt.md").read_text() == "staged question\n"
    assert (turn_path / "response.md").read_text() == "staged answer\n"


def test_clear_discards_the_staged_query(lm: Lm) -> None:
    lm.set_editor_prompt("staged question\n")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("edit-prompt", "--thread", "demo", stdin="")
    result = lm.invoke("clear", "--thread", "demo", stdin="")

    assert result.returncode == 0
    assert not lm.get_staged_path("demo").exists()
    assert list(lm.get_thread_path("demo").glob("[0-9]*")) == []


# --- Thread settings ---


def test_thread_model_reaches_claude(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_response("hi")

    lm.invoke("new", "demo", "--claude-model", "claude-haiku-4-5", stdin="")
    lm.invoke("run", "--thread", "demo", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--model") + 1] == "claude-haiku-4-5"


def test_thread_capability_reaches_claude(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_response("hi")

    lm.invoke("new", "demo", "--with", "web", stdin="")
    lm.invoke("run", "--thread", "demo", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--tools") + 1] == "WebFetch,WebSearch"


def test_a_thread_without_capabilities_gets_no_tools(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_response("hi")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("run", "--thread", "demo", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--tools") + 1] == ""


# --- Refusals ---


def test_run_refuses_while_a_query_is_staged(lm: Lm) -> None:
    lm.set_editor_prompt("staged question\n")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("edit-prompt", "--thread", "demo", stdin="")
    result = lm.invoke("run", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "Staged query already exists" in result.stderr


def test_an_empty_prompt_creates_no_turn(lm: Lm) -> None:
    lm.set_editor_prompt("")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("run", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "Prompt is empty" in result.stderr
    assert not list(lm.get_thread_path("demo").glob("[0-9]*"))


def test_rename_refuses_an_existing_destination(lm: Lm) -> None:
    lm.invoke("new", "before", stdin="")
    lm.invoke("new", "after", stdin="")
    result = lm.invoke("rename", "--thread", "before", "after", stdin="")

    assert result.returncode != 0
    assert "Thread already exists" in result.stderr
    assert lm.get_thread_path("before").is_dir()


def test_rm_refuses_an_unknown_thread(lm: Lm) -> None:
    result = lm.invoke("rm", "--thread", "missing", stdin="")

    assert result.returncode != 0
    assert "Thread does not exist" in result.stderr


def test_commit_refuses_without_a_staged_query(lm: Lm) -> None:
    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("commit", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "No staged query found" in result.stderr


def test_an_unnamed_thread_is_rejected(lm: Lm) -> None:
    result = lm.invoke("new", "../escape", stdin="")

    assert result.returncode != 0
    assert "Invalid thread name" in result.stderr


def test_an_unknown_preset_is_rejected(lm: Lm) -> None:
    lm.set_editor_prompt("go\n")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("run", "--thread", "demo", "--preset", "missing", stdin="")

    assert result.returncode != 0
    assert "Preset not found" in result.stderr


def test_select_refuses_when_nothing_is_picked(lm: Lm) -> None:
    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("run", "--select", stdin="")

    assert result.returncode != 0
    assert "No thread selected" in result.stderr


# --- Details of the saved turn ---


def test_committed_turn_files_are_read_only(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("run", "--thread", "demo", stdin="")

    turn_path = lm.get_turn_path("demo", 0)
    assert (turn_path / "prompt.md").stat().st_mode & 0o222 == 0
    assert (turn_path / "response.md").stat().st_mode & 0o222 == 0


# --- Editor-specific buffer layout ---


def test_vim_gets_the_prompt_below_the_history(lm: Lm) -> None:
    lm.set_editor("vim")
    lm.set_preset("draft", "MY DRAFT")
    lm.set_claude_response("first answer")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.invoke("run", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.invoke("run", "--thread", "demo", "--preset", "draft", stdin="")

    buffer = lm.get_editor_buffer()
    assert buffer.index("first question") < buffer.index("MY DRAFT")


def test_vim_is_told_to_jump_to_the_prompt(lm: Lm) -> None:
    lm.set_editor("vim")
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_response("4")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("run", "--thread", "demo", stdin="")

    assert "+$" in lm.get_editor_argv()


def test_other_editors_get_the_prompt_above_the_history(lm: Lm) -> None:
    lm.set_preset("draft", "MY DRAFT")
    lm.set_claude_response("first answer")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.invoke("run", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.invoke("run", "--thread", "demo", "--preset", "draft", stdin="")

    buffer = lm.get_editor_buffer()
    assert buffer.index("MY DRAFT") < buffer.index("first question")
    assert "+$" not in lm.get_editor_argv()
