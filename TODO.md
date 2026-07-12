# Now
- Print cleanly to stdout (opt-in setting? leverage stderr?).

# Later
- Implement different types of backend, not just Claude.
- Maybe set capabilities both per-turn and per-thread without cache-busting via `--allowed-tools`.
  Note that having `--tools` that are not allowed might be confusing to Claude in `--print` mode.
- Explore Claude's @ directives in depth and how to make the most of them.
  Maybe stdin could become just another file?
  Since we save it on disk anyway.
- Check what the Claude json events look like and extract other useful stuff.
- Inspect `claude` command flags for further improvements.
- Differentate prompt (text part) vs query (the whole) from the POV of the user.
- Address conflict of fzf's bottom-up and less's top-down for thread listing.
- Consider exposing json structured output as option.
  What would be the best interface for it?
- Consider whether to have more than just data as local, like git does (e.g. config overrides).
- Have a setting to specify aliases for models.

# Aspirational
- Metacommands for thread management (Claude understands which thread to clean, which to rename, etc. and comes up with a plan).
  Should this reside in this tool? Perhaps we could consider differentiating this tool (plain lm) vs self-referential utilities (organizing threads is the obvious use case for now).
- Implement forking with symlinks to share common history between threads.
  Seems like we will need to fork at each turn to edit previous messages.
- Allow user to change system prompt and/or model mid-session, and understand implications in terms of session/cache.
