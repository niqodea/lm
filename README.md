# lm

A minimal Claude CLI that runs on your Pro/Max subscription. You own the context.

## What it is

`lm` gives you a tight loop: open your editor, write a prompt, get a response.

It follows UNIX conventions throughout: pipe in context, compose with other tools, store everything as plain text.
Conversations live in `~/.local/share/lm/threads/` as numbered markdown files you can read, edit, grep, or delete.

No API key. No usage-based billing. Just your existing Claude subscription.

## Installation

```sh
make install   # copies lm to ~/.local/bin/lm
lm init        # creates config and data directories
```

Requires the [Claude CLI](https://github.com/anthropics/claude-code) installed and authenticated.

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
lm ls                # list threads with last prompt/response summary
lm new mytopic       # create a named thread
lm rename -t old new # rename a thread
lm rm -t mytopic     # delete a thread
lm show -t mytopic   # print the turns of a thread
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
```

## Presets

Store reusable instructions in `~/.config/lm/presets/<name>.md`. They're prepended to the editor buffer — refine or extend before sending.

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
