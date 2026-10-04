"""End-to-end tests driving the lm CLI as a user would.

Ordered from the plainest intended usage down to the corners: the core loop
first, then the documented workflows, then refusals and details.
"""

from pathlib import Path

from .conftest import Lm
from .stubs.protocol import ClaudeToolCall

# --- The core loop ---


def test_new_creates_a_thread(lm: Lm) -> None:
    result = lm.invoke("new", "demo", stdin="")

    assert result.returncode == 0
    assert lm.get_thread_path("demo").is_dir()


def test_reply_saves_the_prompt_and_the_response(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("reply", "--thread", "demo", stdin="")

    assert result.returncode == 0
    turn_path = lm.get_turn_path("demo", 0)
    assert (turn_path / "prompt.md").read_text() == "what is 2+2?\n"
    assert (turn_path / "response.md").read_text() == "4\n"


def test_reply_sends_the_prompt_to_claude(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")

    assert lm.get_claude_prompt() == "what is 2+2?"


def test_reply_sends_a_prompt_starting_with_a_hyphen(lm: Lm) -> None:
    lm.set_editor_prompt("- first item\n")
    lm.set_claude_result_success("ok")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("reply", "--thread", "demo", stdin="")

    assert result.returncode == 0
    assert lm.get_claude_prompt() == "- first item"


def test_reply_keeps_user_config_out_of_the_turn(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")

    assert "--safe-mode" in lm.get_claude_argv()


def test_reply_prints_the_response(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("reply", "--thread", "demo", stdin="")

    assert "4" in result.stdout


def test_ls_lists_the_thread(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")
    result = lm.invoke("ls", stdin="")

    assert "demo" in result.stdout
    assert "what is 2+2?" in result.stdout
    assert "4" in result.stdout


def test_show_prints_the_exchange(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")
    result = lm.invoke("show", "--thread", "demo", stdin="")

    assert "what is 2+2?" in result.stdout
    assert "4" in result.stdout


# --- Managing threads ---


def test_run_without_a_thread_creates_one(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    result = lm.invoke("run", stdin="")
    ls_result = lm.invoke("ls", stdin="")

    assert result.returncode == 0
    assert "what is 2+2?" in ls_result.stdout


def test_run_with_a_name_creates_that_thread(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    result = lm.invoke("run", "demo", stdin="")

    assert result.returncode == 0
    prompt_path = lm.get_turn_path("demo", 0) / "prompt.md"
    assert prompt_path.read_text() == "what is 2+2?\n"


def test_run_settings_reach_claude(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    lm.invoke(
        "run", "demo", "--claude-model", "claude-opus-5-5", "--with", "web", stdin=""
    )

    argv = lm.get_claude_argv()
    assert argv[argv.index("--model") + 1] == "claude-opus-5-5"
    assert argv[argv.index("--tools") + 1] == "WebFetch,WebSearch"


def test_run_refuses_an_existing_thread(lm: Lm) -> None:
    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("run", "demo", stdin="")

    assert result.returncode != 0
    assert "Thread already exists" in result.stderr
    assert lm.get_editor_buffer() == ""


def test_run_with_an_empty_prompt_creates_no_thread(lm: Lm) -> None:
    lm.set_editor_prompt("")

    result = lm.invoke("run", "demo", stdin="")

    assert result.returncode != 0
    assert not lm.get_thread_path("demo").exists()


def test_run_chat_runs_each_queued_prompt_as_a_turn(lm: Lm) -> None:
    lm.set_claude_result_success("an answer")
    lm.set_editor_prompts(["first question\n", "second question\n"])

    result = lm.invoke("run", "demo", "--chat", stdin="")

    assert result.returncode == 0
    assert (lm.get_turn_path("demo", 0) / "prompt.md").read_text() == "first question\n"
    assert (
        lm.get_turn_path("demo", 1) / "prompt.md"
    ).read_text() == "second question\n"
    # The second turn resumed the session the first one started
    assert lm.get_claude_session_prompts() == ["first question", "second question"]


def test_rename_changes_a_thread_name(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    lm.invoke("new", "before", stdin="")
    lm.invoke("reply", "--thread", "before", stdin="")
    result = lm.invoke("rename", "--thread", "before", "after", stdin="")

    assert result.returncode == 0
    assert not lm.get_thread_path("before").exists()
    assert (lm.get_turn_path("after", 0) / "prompt.md").read_text() == "what is 2+2?\n"


def test_rename_allows_another_turn(lm: Lm) -> None:
    lm.set_claude_result_success("an answer")

    lm.invoke("new", "before", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.invoke("reply", "--thread", "before", stdin="")
    lm.invoke("rename", "--thread", "before", "after", stdin="")
    lm.set_editor_prompt("second question\n")
    result = lm.invoke("reply", "--thread", "after", stdin="")

    assert result.returncode == 0
    assert (
        lm.get_turn_path("after", 1) / "prompt.md"
    ).read_text() == "second question\n"
    # The session followed the thread to its new name
    assert lm.get_claude_session_prompts() == ["first question", "second question"]


def test_rm_deletes_a_thread(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")
    result = lm.invoke("rm", "--thread", "demo", stdin="")

    assert result.returncode == 0
    assert not lm.get_thread_path("demo").exists()


def test_undo_stages_the_last_turn_again(lm: Lm) -> None:
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("what is 2+2?\n")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.set_editor_prompt("and 3+3?\n")
    lm.invoke("reply", "--thread", "demo", stdin="")
    result = lm.invoke("undo", "--thread", "demo", stdin="")
    status_result = lm.invoke("status", "-t", "demo", stdin="")

    assert result.returncode == 0
    turn_paths = list(lm.get_thread_path("demo").glob("[0-9]*"))
    assert len(turn_paths) == 1
    assert (turn_paths[0] / "prompt.md").read_text() == "what is 2+2?\n"
    assert "and 3+3?" in status_result.stdout


def test_a_commit_after_undo_resends_the_undone_prompt(lm: Lm) -> None:
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("what is 2+2?\n")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.set_editor_prompt("and 3+3?\n")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.invoke("undo", "--thread", "demo", stdin="")
    lm.set_claude_result_success("6")
    result = lm.invoke("commit", "--thread", "demo", stdin="")

    assert result.returncode == 0
    assert lm.get_claude_prompt() == "and 3+3?"
    assert lm.get_claude_session_prompts() == ["what is 2+2?", "and 3+3?"]
    assert (lm.get_turn_path("demo", 1) / "response.md").read_text() == "6\n"


def test_an_undone_prompt_can_be_edited_before_it_is_resent(lm: Lm) -> None:
    lm.set_editor("nano")
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("what is 2+2?\n")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.invoke("undo", "--thread", "demo", stdin="")
    lm.set_editor_prompt("what is 3+3?\n")
    lm.invoke("edit-prompt", "--thread", "demo", stdin="")
    lm.invoke("commit", "--thread", "demo", stdin="")

    # The editor stub types below the draft it was handed
    assert lm.get_claude_prompt() == "what is 2+2?\n\nwhat is 3+3?"


def test_a_commit_after_undoing_every_turn_starts_a_new_session(lm: Lm) -> None:
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("what is 2+2?\n")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.invoke("undo", "--thread", "demo", stdin="")
    lm.invoke("commit", "--thread", "demo", stdin="")

    assert "--session-id" in lm.get_claude_argv()
    assert lm.get_claude_session_prompts() == ["what is 2+2?"]


def test_undo_refuses_with_a_staged_query(lm: Lm) -> None:
    lm.set_editor_prompts(["what is 2+2?\n", "and 3+3?\n"])
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.invoke("edit-prompt", "--thread", "demo", stdin="")
    result = lm.invoke("undo", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "Staged query already exists" in result.stderr
    assert len(list(lm.get_thread_path("demo").glob("[0-9]*"))) == 1


def test_undo_refuses_a_thread_without_turns(lm: Lm) -> None:
    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("undo", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "No turns to undo" in result.stderr


def test_last_resumes_the_most_recent_thread(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    lm.invoke("new", "older", stdin="")
    lm.invoke("new", "newer", stdin="")
    result = lm.invoke("reply", "--last", stdin="")

    assert result.returncode == 0
    assert (lm.get_turn_path("newer", 0) / "prompt.md").read_text() == "what is 2+2?\n"


def test_last_picks_the_thread_used_most_recently(lm: Lm) -> None:
    lm.invoke("new", "older", stdin="")
    lm.invoke("new", "newer", stdin="")
    lm.invoke("show", "--thread", "older", stdin="")
    result = lm.invoke("status", "--last", stdin="")

    assert "Thread: older\n" in result.stdout


def test_select_picks_a_thread(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    lm.invoke("new", "wanted", stdin="")
    lm.invoke("new", "other", stdin="")
    lm.set_selected_thread("wanted")
    result = lm.invoke("reply", "--select", stdin="")

    assert result.returncode == 0
    assert (lm.get_turn_path("wanted", 0) / "prompt.md").read_text() == "what is 2+2?\n"


# --- Feeding context in ---


def test_piped_stdin_reaches_claude(lm: Lm) -> None:
    lm.set_editor_prompt("summarize this\n")
    lm.set_claude_result_success("done")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="PIPED CONTEXT")

    assert lm.get_claude_stdin() == "PIPED CONTEXT"


def test_piped_stdin_is_saved_with_the_turn(lm: Lm) -> None:
    lm.set_editor_prompt("summarize this\n")
    lm.set_claude_result_success("done")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="PIPED CONTEXT")

    assert (lm.get_turn_path("demo", 0) / "stdin").read_text() == "PIPED CONTEXT"


def test_piped_stdin_does_not_reach_the_editor(lm: Lm) -> None:
    lm.set_editor_prompt("summarize this\n")
    lm.set_claude_result_success("done")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="PIPED CONTEXT")

    # The editor is handed the terminal, never the pipe lm was given
    assert "PIPED CONTEXT" not in lm.get_editor_buffer()


def test_attachment_is_saved_with_the_turn(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("read this\n")
    lm.set_claude_result_success("read it")
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("ATTACHED TEXT")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", "--attach", str(attachment_path), stdin="")

    saved_path = lm.get_turn_path("demo", 0) / "attachments" / "notes.md"
    assert saved_path.read_text() == "ATTACHED TEXT"


def test_attachment_is_announced_to_claude(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("read this\n")
    lm.set_claude_result_success("read it")
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("ATTACHED TEXT")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", "--attach", str(attachment_path), stdin="")

    assert "- @notes.md" in lm.get_claude_prompt()


def test_attachment_alias_renames_the_saved_file(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("read this\n")
    lm.set_claude_result_success("read it")
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("ATTACHED TEXT")

    lm.invoke("new", "demo", stdin="")
    lm.invoke(
        "reply",
        "--thread",
        "demo",
        "--attach",
        f"{attachment_path}:renamed.md",
        stdin="",
    )

    attachments_path = lm.get_turn_path("demo", 0) / "attachments"
    assert (attachments_path / "renamed.md").read_text() == "ATTACHED TEXT"
    assert not (attachments_path / "notes.md").exists()


def test_a_preset_is_offered_as_a_draft(lm: Lm) -> None:
    lm.set_preset("review", "REVIEW THIS CODE")
    lm.set_editor_prompt("go\n")
    lm.set_claude_result_success("ok")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", "--preset", "review", stdin="")

    assert "REVIEW THIS CODE" in lm.get_editor_buffer()


# --- Several turns ---


def test_a_second_reply_starts_a_second_turn(lm: Lm) -> None:
    lm.set_claude_result_success("an answer")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.invoke("reply", "--thread", "demo", stdin="")

    assert (lm.get_turn_path("demo", 0) / "prompt.md").read_text() == "first question\n"
    assert (
        lm.get_turn_path("demo", 1) / "prompt.md"
    ).read_text() == "second question\n"


def test_past_turns_appear_in_the_editor(lm: Lm) -> None:
    lm.set_claude_result_success("first answer")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.invoke("reply", "--thread", "demo", stdin="")

    buffer = lm.get_editor_buffer()
    assert "first question" in buffer
    assert "first answer" in buffer


def test_past_turns_are_not_resent_to_claude(lm: Lm) -> None:
    lm.set_claude_result_success("first answer")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.invoke("reply", "--thread", "demo", stdin="")

    # The session carries the history, so only the new prompt is sent
    assert "first question" not in lm.get_claude_prompt()


def test_a_second_turn_resumes_the_session(lm: Lm) -> None:
    lm.set_claude_result_success("an answer")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.invoke("reply", "--thread", "demo", stdin="")

    # The second turn grew the session the first turn started
    assert lm.get_claude_session_prompts() == ["first question", "second question"]


def test_threads_keep_separate_sessions(lm: Lm) -> None:
    lm.set_claude_result_success("an answer")

    lm.invoke("new", "one", stdin="")
    lm.invoke("new", "two", stdin="")
    lm.set_editor_prompt("question for one\n")
    lm.invoke("reply", "--thread", "one", stdin="")
    lm.set_editor_prompt("question for two\n")
    lm.invoke("reply", "--thread", "two", stdin="")
    lm.set_editor_prompt("another question for one\n")
    lm.invoke("reply", "--thread", "one", stdin="")

    assert lm.get_claude_session_prompts() == [
        "question for one",
        "another question for one",
    ]


def test_chat_runs_each_queued_prompt_as_a_turn(lm: Lm) -> None:
    lm.set_claude_result_success("an answer")
    lm.set_editor_prompts(["first question\n", "second question\n"])

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("reply", "--chat", "--thread", "demo", stdin="")

    assert result.returncode == 0
    assert (lm.get_turn_path("demo", 0) / "prompt.md").read_text() == "first question\n"
    assert (
        lm.get_turn_path("demo", 1) / "prompt.md"
    ).read_text() == "second question\n"


def test_reply_reports_a_compacted_session(lm: Lm) -> None:
    lm.set_editor_prompt("a question\n")
    lm.set_claude_result_success_with_compaction("", 190000, "an answer")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("reply", "--thread", "demo", stdin="")

    assert "Compacted session at 190000 tokens" in result.stderr
    assert (lm.get_turn_path("demo", 0) / "response.md").read_text() == "an answer\n"


def test_a_compaction_starts_a_new_paragraph(lm: Lm) -> None:
    lm.set_editor_prompt("a question\n")
    lm.set_claude_result_success_with_compaction("first half", 190000, "second half")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("reply", "--thread", "demo", stdin="")

    # The notice goes to stderr, so it never lands inside the saved response
    assert "Compacted session at 190000 tokens" in result.stderr
    assert (
        lm.get_turn_path("demo", 0) / "response.md"
    ).read_text() == "first half\n\nsecond half\n"


def test_a_tool_call_shows_in_the_response(lm: Lm) -> None:
    lm.set_editor_prompt("a question\n")
    lm.set_claude_result_success_with_tool_calls(
        "looking it up",
        [ClaudeToolCall(name="WebSearch", arguments={"query": "lm cli"})],
        "found it",
    )

    lm.invoke("new", "demo", "--with", "web", stdin="")
    result = lm.invoke("reply", "--thread", "demo", stdin="")

    assert 'Running tool: WebSearch(query="lm cli")' in result.stdout
    assert (lm.get_turn_path("demo", 0) / "response.md").read_text() == (
        'looking it up\n\n> Running tool: WebSearch(query="lm cli")\n\nfound it\n'
    )


def test_a_tool_call_before_any_text_opens_the_response(lm: Lm) -> None:
    lm.set_editor_prompt("a question\n")
    lm.set_claude_result_success_with_tool_calls(
        "", [ClaudeToolCall(name="Now", arguments={})], "found it"
    )

    lm.invoke("new", "demo", "--with", "web", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")

    assert (
        lm.get_turn_path("demo", 0) / "response.md"
    ).read_text() == "> Running tool: Now()\n\nfound it\n"


def test_a_tool_call_after_a_tool_call_starts_a_new_paragraph(lm: Lm) -> None:
    lm.set_editor_prompt("a question\n")
    lm.set_claude_result_success_with_tool_calls(
        "",
        [
            ClaudeToolCall(name="WebSearch", arguments={"query": "lm"}),
            ClaudeToolCall(name="WebFetch", arguments={"url": "https://lm.dev"}),
        ],
        "found it",
    )

    lm.invoke("new", "demo", "--with", "web", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")

    assert (lm.get_turn_path("demo", 0) / "response.md").read_text() == (
        '> Running tool: WebSearch(query="lm")\n\n'
        '> Running tool: WebFetch(url="https://lm.dev")\n\n'
        "found it\n"
    )


def test_a_tool_call_shows_every_argument_it_was_given(lm: Lm) -> None:
    lm.set_editor_prompt("a question\n")
    lm.set_claude_result_success_with_tool_calls(
        "",
        [
            ClaudeToolCall(
                name="WebFetch",
                arguments={"url": "https://lm.dev", "timeout": 30, "raw": False},
            )
        ],
        "found it",
    )

    lm.invoke("new", "demo", "--with", "web", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")

    assert (lm.get_turn_path("demo", 0) / "response.md").read_text() == (
        '> Running tool: WebFetch(url="https://lm.dev", timeout=30, raw=false)\n\n'
        "found it\n"
    )


# --- The staged workflow ---


def test_edit_prompt_stages_a_prompt(lm: Lm) -> None:
    lm.set_editor_prompt("staged question\n")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("edit-prompt", "--thread", "demo", stdin="")
    status_result = lm.invoke("status", "-t", "demo", stdin="")

    assert result.returncode == 0
    assert "staged question" in status_result.stdout


def test_an_abandoned_edit_prompt_leaves_nothing_staged(lm: Lm) -> None:
    lm.set_editor_prompt("")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("edit-prompt", "--thread", "demo", stdin="")
    status_result = lm.invoke("status", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "Nothing staged." in status_result.stdout


def test_status_shows_the_staged_query(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("staged question\n")
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("ATTACHED TEXT")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("edit-prompt", "--thread", "demo", stdin="")
    lm.invoke("attach", "--thread", "demo", str(attachment_path), stdin="")
    result = lm.invoke("status", "--thread", "demo", stdin="")

    assert result.returncode == 0
    assert "staged question" in result.stdout
    assert "notes.md" in result.stdout


def test_status_reports_a_thread_with_nothing_staged(lm: Lm) -> None:
    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("status", "--thread", "demo", stdin="")

    assert result.returncode == 0
    assert "Nothing staged." in result.stdout


def test_attach_adds_to_the_staged_query(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("staged question\n")
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("ATTACHED TEXT")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("edit-prompt", "--thread", "demo", stdin="")
    result = lm.invoke("attach", "--thread", "demo", str(attachment_path), stdin="")
    lm.invoke("commit", "--thread", "demo", stdin="")

    assert result.returncode == 0
    saved_path = lm.get_turn_path("demo", 0) / "attachments" / "notes.md"
    assert saved_path.read_text() == "ATTACHED TEXT"


def test_commit_turns_the_staged_query_into_a_turn(lm: Lm) -> None:
    lm.set_editor_prompt("staged question\n")
    lm.set_claude_result_success("staged answer")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("edit-prompt", "--thread", "demo", stdin="")
    result = lm.invoke("commit", "--thread", "demo", stdin="")
    status_result = lm.invoke("status", "-t", "demo", stdin="")

    assert result.returncode == 0
    assert "Nothing staged." in status_result.stdout
    turn_path = lm.get_turn_path("demo", 0)
    assert (turn_path / "prompt.md").read_text() == "staged question\n"
    assert (turn_path / "response.md").read_text() == "staged answer\n"


def test_clear_discards_the_staged_query(lm: Lm) -> None:
    lm.set_editor_prompt("staged question\n")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("edit-prompt", "--thread", "demo", stdin="")
    result = lm.invoke("clear", "--thread", "demo", stdin="")
    status_result = lm.invoke("status", "-t", "demo", stdin="")

    assert result.returncode == 0
    assert "Nothing staged." in status_result.stdout
    assert list(lm.get_thread_path("demo").glob("[0-9]*")) == []


# --- Thread settings ---


def test_thread_model_reaches_claude(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_result_success("hi")

    lm.invoke("new", "demo", "--claude-model", "claude-haiku-4-5", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--model") + 1] == "claude-haiku-4-5"


def test_a_model_alias_reaches_claude_as_the_model_it_names(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_result_success("hi")
    lm.set_settings('[models]\nfast = "claude-haiku-4-5"\n')

    lm.invoke("new", "demo", "--claude-model", "fast", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--model") + 1] == "claude-haiku-4-5"


def test_the_default_model_reaches_a_thread_that_names_none(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_result_success("hi")
    lm.set_settings('[defaults]\nmodel = "claude-opus-5-5"\neffort = "high"\n')

    lm.invoke("run", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--model") + 1] == "claude-opus-5-5"
    assert argv[argv.index("--effort") + 1] == "high"


def test_a_default_model_can_be_an_alias(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_result_success("hi")
    lm.set_settings('[defaults]\nmodel = "fast"\n[models]\nfast = "claude-haiku-4-5"\n')

    lm.invoke("run", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--model") + 1] == "claude-haiku-4-5"


def test_a_thread_gets_the_built_in_defaults_when_settings_name_none(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_result_success("hi")

    lm.invoke("run", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--model") + 1] == "claude-sonnet-5"
    assert argv[argv.index("--effort") + 1] == "medium"


def test_an_unknown_default_effort_is_rejected(lm: Lm) -> None:
    lm.set_settings('[defaults]\neffort = "huge"\n')

    result = lm.invoke("new", "demo", stdin="")

    assert result.returncode != 0
    assert "Unknown Claude effort: huge" in result.stderr


def test_a_bad_output_setting_is_rejected_before_any_turn(lm: Lm) -> None:
    lm.set_settings('[output]\nchar_delay = "fast"\n')

    result = lm.invoke("new", "demo", stdin="")

    assert result.returncode != 0
    assert "Setting output.char_delay must be a float: fast" in result.stderr
    assert not lm.get_thread_path("demo").exists()


def test_a_bad_model_alias_is_rejected_even_if_unused(lm: Lm) -> None:
    lm.set_settings("[models]\nfast = 3\n")

    result = lm.invoke("new", "demo", stdin="")

    assert result.returncode != 0
    assert "Model alias fast must be a string: 3" in result.stderr


def test_thread_effort_reaches_claude(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_result_success("hi")

    lm.invoke("new", "demo", "--claude-effort", "high", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--effort") + 1] == "high"


def test_the_default_system_prompt_reaches_a_thread_that_names_none(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_result_success("hi")
    lm.set_default_system_prompt("Answer as a sommelier.")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--system-prompt") + 1] == "Answer as a sommelier."


def test_thread_system_prompt_reaches_claude(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_result_success("hi")

    lm.set_system_prompt("pirate", "Answer as a pirate.")

    lm.invoke("new", "demo", "--system-prompt", "pirate", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--system-prompt") + 1] == "Answer as a pirate."


def test_thread_capability_reaches_claude(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_result_success("hi")

    lm.invoke("new", "demo", "--with", "web", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--tools") + 1] == "WebFetch,WebSearch"


def test_status_shows_the_thread_settings(lm: Lm) -> None:
    lm.set_system_prompt("pirate", "Answer as a pirate.")

    lm.invoke(
        "new",
        "demo",
        "--claude-model",
        "claude-haiku-4-5",
        "--system-prompt",
        "pirate",
        "--with",
        "web",
        stdin="",
    )
    result = lm.invoke("status", "--thread", "demo", stdin="")

    assert result.returncode == 0
    assert "claude-haiku-4-5" in result.stdout
    assert "Answer as a pirate." in result.stdout
    assert "WebFetch" in result.stdout


def test_a_thread_without_capabilities_gets_no_tools(lm: Lm) -> None:
    lm.set_editor_prompt("hello\n")
    lm.set_claude_result_success("hi")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")

    argv = lm.get_claude_argv()
    assert argv[argv.index("--tools") + 1] == ""


# --- Refusals ---


def test_an_empty_prompt_creates_no_turn(lm: Lm) -> None:
    lm.set_editor_prompt("")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("reply", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "Prompt is empty" in result.stderr
    assert not list(lm.get_thread_path("demo").glob("[0-9]*"))


def test_lm_without_a_command_shows_the_usage(lm: Lm) -> None:
    result = lm.invoke(stdin="")

    assert result.returncode != 0
    assert "the following arguments are required: command" in result.stderr


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


def test_reply_reports_a_failed_inference(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_error("", "error_max_turns", [])

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("reply", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "hit the turn limit" in result.stderr
    assert "lm commit -t demo" in result.stderr


def test_a_failed_inference_leaves_the_query_staged(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_error("", "error_during_execution", [])

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.set_claude_result_success("4")
    result = lm.invoke("commit", "--thread", "demo", stdin="")

    assert result.returncode == 0
    assert lm.get_claude_prompt() == "what is 2+2?"


def test_a_retried_first_turn_is_in_the_session_once(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_error("", "error_during_execution", [])

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.set_claude_result_success("4")
    lm.invoke("commit", "--thread", "demo", stdin="")

    assert lm.get_claude_session_prompts() == ["what is 2+2?"]


def test_a_retried_later_turn_is_in_the_session_once(lm: Lm) -> None:
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("what is 2+2?\n")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.set_editor_prompt("and 3+3?\n")
    lm.set_claude_result_absent("6")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.set_claude_result_success("6")
    lm.invoke("commit", "--thread", "demo", stdin="")

    assert lm.get_claude_session_prompts() == ["what is 2+2?", "and 3+3?"]


def test_reply_reports_the_error_text_claude_gave(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_error(
        "", "error_max_turns", ["Reached maximum number of turns (30)"]
    )

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("reply", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "Reached maximum number of turns (30)" in result.stderr


def test_an_unknown_failure_names_its_subtype(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_error("", "error_invented_later", [])

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("reply", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "error_invented_later" in result.stderr


def test_reply_reports_a_stream_without_a_result(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_absent("4")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("reply", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "without reporting a result" in result.stderr
    assert not list(lm.get_thread_path("demo").glob("[0-9]*"))


def test_reply_refuses_with_a_staged_query(lm: Lm) -> None:
    lm.set_editor_prompt("staged question\n")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("edit-prompt", "--thread", "demo", stdin="")
    result = lm.invoke("reply", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "Staged query already exists" in result.stderr
    assert "lm status -t demo" in result.stderr


def test_commit_refuses_without_a_staged_query(lm: Lm) -> None:
    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("commit", "--thread", "demo", stdin="")

    assert result.returncode != 0
    assert "No staged query found" in result.stderr


def test_an_invalid_thread_name_is_rejected(lm: Lm) -> None:
    result = lm.invoke("new", "../escape", stdin="")

    assert result.returncode != 0
    assert "Invalid thread name" in result.stderr


def test_an_unknown_system_prompt_is_rejected(lm: Lm) -> None:
    result = lm.invoke("new", "demo", "--system-prompt", "missing", stdin="")

    assert result.returncode != 0
    assert "System prompt not found" in result.stderr
    assert not lm.get_thread_path("demo").exists()


def test_an_alias_that_leaves_the_attachments_is_rejected(
    lm: Lm, tmp_path: Path
) -> None:
    lm.set_editor_prompt("read this\n")
    attachment_path = tmp_path / "notes.md"
    attachment_path.write_text("ATTACHED TEXT")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke(
        "reply", "--thread", "demo", "--attach", f"{attachment_path}:../x", stdin=""
    )

    assert result.returncode != 0
    assert "Attachment alias is not a file name: ../x" in result.stderr
    assert list(lm.get_thread_path("demo").rglob("x")) == []


def test_run_refuses_two_attachments_with_one_alias(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("read these\n")
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "notes.md").write_text("FIRST")
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / "notes.md").write_text("SECOND")

    result = lm.invoke(
        "run",
        "demo",
        "--attach",
        str(tmp_path / "a" / "notes.md"),
        "--attach",
        str(tmp_path / "b" / "notes.md"),
        stdin="",
    )

    assert result.returncode != 0
    assert "Attachment alias given twice: notes.md" in result.stderr
    assert not lm.get_thread_path("demo").exists()


def test_attach_refuses_an_alias_already_staged(lm: Lm, tmp_path: Path) -> None:
    lm.set_editor_prompt("read these\n")
    first_path = tmp_path / "notes.md"
    first_path.write_text("FIRST")
    (tmp_path / "other").mkdir()
    second_path = tmp_path / "other" / "notes.md"
    second_path.write_text("SECOND")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("edit-prompt", "--thread", "demo", stdin="")
    lm.invoke("attach", "--thread", "demo", str(first_path), stdin="")
    result = lm.invoke("attach", "--thread", "demo", str(second_path), stdin="")

    assert result.returncode != 0
    assert "Attachment already exists with alias 'notes.md'" in result.stderr
    staged_path = lm.get_thread_path("demo") / "STAGED" / "attachments" / "notes.md"
    assert staged_path.read_text() == "FIRST"


def test_an_unknown_preset_is_rejected(lm: Lm) -> None:
    lm.set_editor_prompt("go\n")

    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("reply", "--thread", "demo", "--preset", "missing", stdin="")

    assert result.returncode != 0
    assert "Preset not found" in result.stderr


def test_select_tells_apart_names_that_shorten_the_same(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    # Both names shorten to "project...notes" in the list fzf shows
    lm.invoke("new", "project-alpha-notes", stdin="")
    lm.invoke("new", "project-beta-notes", stdin="")
    lm.set_selected_thread("project-alpha-notes")
    result = lm.invoke("reply", "--select", stdin="")

    assert result.returncode == 0
    prompt_path = lm.get_turn_path("project-alpha-notes", 0) / "prompt.md"
    assert prompt_path.read_text() == "what is 2+2?\n"


def test_select_refuses_when_nothing_is_picked(lm: Lm) -> None:
    lm.invoke("new", "demo", stdin="")
    result = lm.invoke("reply", "--select", stdin="")

    assert result.returncode != 0
    assert "No thread selected" in result.stderr


# --- Details of the saved turn ---


def test_committed_turn_files_are_read_only(lm: Lm) -> None:
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")

    turn_path = lm.get_turn_path("demo", 0)
    assert (turn_path / "prompt.md").stat().st_mode & 0o222 == 0
    assert (turn_path / "response.md").stat().st_mode & 0o222 == 0


def test_a_turn_takes_the_whole_session_claude_wrote(lm: Lm) -> None:
    lm.set_claude_result_success("an answer")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("a question\n")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.set_editor_prompt("another question\n")
    lm.invoke("reply", "--thread", "demo", stdin="")

    # Claude is still writing the session when it reports its result, so a turn
    # that moves the file without waiting takes half of it and leaves the rest
    assert lm.get_claude_session_prompts() == ["a question", "another question"]
    assert list(lm.get_claude_projects_path().iterdir()) == []


# --- Editor-specific buffer layout ---


def test_vim_gets_the_prompt_below_the_history(lm: Lm) -> None:
    lm.set_editor("vim")
    lm.set_preset("draft", "MY DRAFT")
    lm.set_claude_result_success("first answer")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.invoke("reply", "--thread", "demo", "--preset", "draft", stdin="")

    buffer = lm.get_editor_buffer()
    assert buffer.index("first question") < buffer.index("MY DRAFT")
    # The half below the scissors line is the one lm reads back, draft included
    assert (
        lm.get_turn_path("demo", 1) / "prompt.md"
    ).read_text() == "MY DRAFT\nsecond question\n"


def test_vim_is_told_to_jump_to_the_prompt(lm: Lm) -> None:
    lm.set_editor("vim")
    lm.set_editor_prompt("what is 2+2?\n")
    lm.set_claude_result_success("4")

    lm.invoke("new", "demo", stdin="")
    lm.invoke("reply", "--thread", "demo", stdin="")

    assert "+$" in lm.get_editor_argv()


def test_nano_gets_the_prompt_above_the_history(lm: Lm) -> None:
    lm.set_editor("nano")
    lm.set_preset("draft", "MY DRAFT")
    lm.set_claude_result_success("first answer")

    lm.invoke("new", "demo", stdin="")
    lm.set_editor_prompt("first question\n")
    lm.invoke("reply", "--thread", "demo", stdin="")
    lm.set_editor_prompt("second question\n")
    lm.invoke("reply", "--thread", "demo", "--preset", "draft", stdin="")

    buffer = lm.get_editor_buffer()
    assert buffer.index("MY DRAFT") < buffer.index("first question")
    assert "+$" not in lm.get_editor_argv()
