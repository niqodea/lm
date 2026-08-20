"""Files the harness and the stubs pass data through.

The stubs run as their own processes, so each file below is one channel between
a test and a stub. An environment variable holds the path of each.
"""

# Written by the harness before the run, read by the stub during it
EDITOR_PROMPT_ENV = "LM_TEST_EDITOR_PROMPT"
CLAUDE_RESPONSE_ENV = "LM_TEST_CLAUDE_RESPONSE"

# Written by the stub during the run, read by the harness after it
EDITOR_BUFFER_ENV = "LM_TEST_EDITOR_BUFFER"
EDITOR_ARGV_ENV = "LM_TEST_EDITOR_ARGV"
CLAUDE_ARGV_ENV = "LM_TEST_CLAUDE_ARGV"
CLAUDE_STDIN_ENV = "LM_TEST_CLAUDE_STDIN"

STUB_FILE_ENVS = (
    EDITOR_PROMPT_ENV,
    CLAUDE_RESPONSE_ENV,
    EDITOR_BUFFER_ENV,
    EDITOR_ARGV_ENV,
    CLAUDE_ARGV_ENV,
    CLAUDE_STDIN_ENV,
)
