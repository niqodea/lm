"""Files the harness and the stubs pass data through.

The stubs run as their own processes, so each file below is one channel between
a test and a stub. An environment variable holds the path of each.
"""

# Written by the harness before the run, read by the stub during it
EDITOR_PROMPTS_ENV = "LM_TEST_EDITOR_PROMPTS"
CLAUDE_RESPONSE_ENV = "LM_TEST_CLAUDE_RESPONSE"
CLAUDE_ERROR_ENV = "LM_TEST_CLAUDE_ERROR"
CLAUDE_NO_RESULT_ENV = "LM_TEST_CLAUDE_NO_RESULT"
FZF_MATCH_ENV = "LM_TEST_FZF_MATCH"

# Written by the stub during the run, read by the harness after it
EDITOR_BUFFER_ENV = "LM_TEST_EDITOR_BUFFER"
EDITOR_ARGV_ENV = "LM_TEST_EDITOR_ARGV"
CLAUDE_ARGV_ENV = "LM_TEST_CLAUDE_ARGV"
CLAUDE_STDIN_ENV = "LM_TEST_CLAUDE_STDIN"

STUB_FILE_ENVS = (
    EDITOR_PROMPTS_ENV,
    CLAUDE_RESPONSE_ENV,
    CLAUDE_ERROR_ENV,
    CLAUDE_NO_RESULT_ENV,
    FZF_MATCH_ENV,
    EDITOR_BUFFER_ENV,
    EDITOR_ARGV_ENV,
    CLAUDE_ARGV_ENV,
    CLAUDE_STDIN_ENV,
)

# The editor takes one prompt per run, so a queue of them drives a chat loop
PROMPT_SEPARATOR = "\n<!-- next prompt -->\n"
