# Later
- Implement different types of backend, not just Claude.
- Maybe set capabilities both per-turn and per-thread without cache-busting via `--allowed-tools`.
  Note that having `--tools` that are not allowed might be confusing to Claude in `--print` mode.
- Explore Claude's @ directives in depth and how to make the most of them.
  Maybe stdin could become just another file?
  Since we save it on disk anyway.
- Check what the Claude json events look like and extract other useful stuff.
- Differentate prompt (text part) vs query (the whole) from the POV of the user.
- Consider exposing json structured output as option.
  What would be the best interface for it?
- Consider whether to have more than just data as local, like git does (e.g. config overrides).
- Make the system prompt a thread setting, like model, effort and tools.
  Presets are a different thing: they seed the editor buffer, not the turn.
- Track the session file by line count instead of parsing it.
  A count stored per turn detects the residue a failed turn leaves behind, and makes undoing a turn a truncation.
  Its records are the interactive CLI's own state (atis-latch, ai-title, queue-operation), so reading them bets on names nobody promised.
  Verify first that claude only ever appends, and that it resumes from a truncated file.

# Aspirational
- Metacommands for thread management (Claude understands which thread to clean, which to rename, etc. and comes up with a plan).
  Should this reside in this tool? Perhaps we could consider differentiating this tool (plain lm) vs self-referential utilities (organizing threads is the obvious use case for now).
- Implement forking with symlinks to share common history between threads.
  `claude --fork-session` resumes into a new session id, which may beat sharing the file.
  Seems like we will need to fork at each turn to edit previous messages.
- Allow user to change system prompt and/or model mid-session, and understand implications in terms of session/cache.
