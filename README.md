# lm

A minimal Claude CLI running on your Pro/Max subscription, where you control the context.

## What it is

`lm` opens your editor, you write a prompt, Claude responds. That's the whole loop.

Pipe in context from your terminal, use presets for recurring tasks, and pick up threads by name.
Everything is plain markdown files in `~/.config/lm/`: readable, editable, and yours.

## Installation

```sh
make install   # copies lm to ~/.local/bin/lm
```

Requires the [Claude CLI](https://github.com/anthropics/claude-code) to be installed and authenticated.

## Usage

Open an editor to write your prompt:

```sh
lm
```

Pipe in context. It lands under a `# lm Context` section in the editor:

```sh
cat somefile.py | lm
git diff | lm
```

Use a preset to pre-populate the editor with reusable instructions:

```sh
lm --preset review
cat foo.py | lm --preset review
```

Continue a named thread:

```sh
lm --thread mytopic
cat error.log | lm --thread mytopic
```

When resuming a thread, past exchanges appear in the editor below a scissors line.
Everything above the line is your new query.
The history is there for context, not for sending.

## Presets

Store reusable instructions in `~/.config/lm/prompts/<name>.md`.
They are prepended to the editor buffer on each run, so you can refine or extend them before sending.

## Threads

Each run creates a thread under `~/.config/lm/threads/`.
Without `--thread`, it's named after the current timestamp.
Pass `--thread <name>` to resume or start a named thread.

Thread history is plain files: numbered query/answer pairs (`00A.md`, `00B.md`, `01A.md`, …) you can read, edit, or delete like anything else.
