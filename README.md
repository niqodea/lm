# lm

A minimal CLI wrapper that pipes your terminal into Claude's intelligence — stateless, tool-free, and billed to your **Claude Pro subscription** rather than the API.

## What it is

`lm` is a thin shell around the `claude` CLI that strips away everything except the core text-in / text-out loop:

- **Stateless**: no memory, no sessions, no conversation history leaking between runs
- **Tool-free**: no file system access, no code execution, no side-effects
- **Subscription-billed**: uses your Claude Pro account, not API credits
- **Model-agnostic by design**: the interface is plain text; swap the backend without changing your workflow

The goal is to give you a sharp, distraction-free interface to the model's raw reasoning ability.

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

Pipe context in (appended under a `# lm Context` section):
```sh
cat somefile.py | lm
git diff | lm
```

Use a saved prompt preset:
```sh
lm --preset review        # loads ~/.config/lm/prompts/review.md
cat foo.py | lm --preset review
```

## Presets

Store reusable system-level instructions in `~/.config/lm/prompts/<name>.md`.
They are prepended to the prompt before you open the editor, so you can refine or extend them per-run.
