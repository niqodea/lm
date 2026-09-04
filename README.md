# lm

A minimal Claude CLI that runs on your Pro/Max subscription. You own the context.

## What it is

`lm` gives you a tight loop: open your editor, write a prompt, get a response.

No API key. No usage-based billing. Just your existing Claude subscription.

## Why not just use `claude`

Same subscription, same models, a smaller tool around them: UNIX conventions throughout, plain files, and nothing that happens without you asking for it.

- **Your conversations are files.** `claude` keeps sessions in an internal format, keyed to the directory you launched it from. `lm` writes every prompt and response as markdown you can grep across, edit, or delete — and threads are topics, so you resume `debug` from anywhere.
- **Nothing comes along for the ride.** Every turn runs in an empty directory with your Claude Code configuration switched off: no `CLAUDE.md`, no hooks, no skills, no tools, nothing read from disk unless you attached it yourself.
- **No surprising defaults.** A thread's model and capabilities are fixed when you create it, and finished turns are written read-only. Nothing changes under you between one turn and the next.
- **Your editor is the prompt box.** Write a long prompt the way you write everything else, with the past exchanges visible below the scissors line while you do.
- **It composes.** `cat main.py | lm run`, `lm show -t debug | pbcopy`. A REPL cannot sit in a pipeline.

For agentic work on a codebase (tools, edits, permissions), keep using `claude`. `lm` is for asking questions and keeping the answers.

## File layout

```
~/.config/lm/
  settings.toml
  presets/

~/.local/share/lm/threads/<name>/
  00/
    prompt.md
    response.md
    attachments/
  01/
    ...
```

Every file is plain markdown. Nothing is hidden, nothing is locked in.

## Installation

```sh
make install   # copies lm to ~/.local/bin/lm
lm init        # creates config and data directories
```

Requires Python 3.14 and the [Claude CLI](https://github.com/anthropics/claude-code), installed and authenticated.

## Usage

### Run

Open your editor, write a prompt, get a response:

```sh
lm run
```

Pipe in context:

```sh
cat main.py | lm run
git diff | lm run
```

Attach files:

```sh
lm run --attach schema.sql --attach notes.md
```

Use a preset:

```sh
lm run --preset review
cat foo.py | lm run --preset review
```

### Threads

Every run creates a new thread. Use `--thread` to name one and resume it across sessions:

```sh
lm run --thread refactor
cat error.log | lm run --thread debug
```

When resuming, past exchanges appear in the editor below a scissors line — visible for context, not sent again.

Pick up where you left off:

```sh
lm run --last          # resume the most recent thread
lm run --select        # pick interactively with fzf
```

### Chat

Loop continuously in a single thread:

```sh
lm chat
lm chat --thread mytopic
```

### Managing threads

```sh
lm ls                 # list threads with last prompt/response summary
lm new mytopic        # create a named thread
lm rename -t old new  # rename a thread
lm rm -t mytopic      # delete a thread
lm show -t mytopic    # print the turns of a thread
lm status -t mytopic  # show a thread's settings and staged query
```

Create a thread with specific capabilities or model:

```sh
lm new research --with web
lm new fast --claude-model claude-haiku-4-5
```

### Staged workflow

For more control, build a query incrementally before sending:

```sh
lm edit-prompt --thread mytopic          # write or revise the prompt
lm attach --thread mytopic schema.sql    # add attachments
lm commit --thread mytopic               # run inference
lm clear --thread mytopic                # discard without sending
lm status --thread mytopic               # see what is staged
```

## Presets

Store reusable instructions in `~/.config/lm/presets/<name>.md`. They're prepended to the editor buffer — refine or extend before sending.

## How it works

`lm` shells out to `claude --print --output-format stream-json` and streams the text back as it arrives.
A thread resumes by symlinking the session file Claude Code keeps, which is an internal detail that could change.
Every turn runs in an empty scratch directory under `--safe-mode`, so neither the directory you are in nor your Claude Code configuration reaches the turn.

None of that is essential to Claude in particular: any backend offering the same kind of call — non-interactive, resumable, streaming — could sit in its place.
The Claude-specific pieces are confined to the inference path and named for it, and turning that into a proper backend interface, with other backends behind it, is the next thing planned.
