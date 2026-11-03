### Category: Shell Scripting and Automation

Tasks involving shell script development, debugging, optimization, and cross-platform compatibility. Focus on robust scripting practices and terminal automation.

**The examples below are for inspiration only. Be creative and design your own unique task!**

**Task Pattern Ideas**:

*Script Development & Debugging:*
- Write robust bash scripts with proper error handling (set -euo pipefail, trap)
- Debug shell scripts with subtle bugs (quoting issues, word splitting, glob expansion)
- Fix scripts that fail on edge cases (empty input, special characters, spaces in filenames)
- Implement signal handling and graceful shutdown in long-running scripts
- Write scripts that handle concurrent execution safely (file locking, atomic operations)

*Cross-Platform Compatibility:*
- Port bash scripts to POSIX sh for portability
- Fix bashisms in scripts that need to run on dash/ash/busybox
- Write scripts that detect and adapt to different environments (Linux/macOS/BSD)
- Handle differences in command options across platforms (GNU vs BSD tools)

*Advanced Shell Features:*
- Complex pipelines with process substitution and named pipes
- Implement command-line argument parsing (getopts, manual parsing)
- Write shell functions with proper scoping and return values
- Use arrays, associative arrays, and parameter expansion effectively
- Implement retry logic with exponential backoff

*Build & Task Automation:*
- Write Makefiles with proper dependency tracking
- Create task runners and build scripts
- Implement file watching and auto-rebuild scripts
- Write deployment and release automation scripts
- Create interactive installation scripts with user prompts

*Cron & Scheduled Tasks:*
- Debug cron jobs that fail silently (environment, PATH issues)
- Write cron scripts with proper logging and error notification
- Implement job scheduling with dependencies
- Handle concurrent cron job execution (locking)

**Skills & Tools** (tag suggestions for your task):
- Core: `bash`, `shell`, `scripting`, `automation`, `posix`
- Tools: `make`, `awk`, `sed`, `xargs`, `find`, `parallel`
- Concepts: `error-handling`, `signal-handling`, `portability`, `idempotency`
- Testing: `shellcheck`, `bats`, `shunit2`

**Possible Input Data** (be creative with environment files!):
- Buggy shell scripts with subtle issues
- Scripts with bashisms that need POSIX conversion
- Makefiles with missing or incorrect dependencies
- Cron job configurations and logs
- Environment dumps showing PATH and variable issues
- Test cases with edge case inputs (special chars, unicode, empty)

**Verification Approaches**:
- Script runs successfully with various inputs (normal, edge cases, empty)
- ShellCheck passes with no errors/warnings
- Script is portable (runs on bash, dash, zsh)
- Error conditions are handled gracefully
- Exit codes are correct for success/failure
- Output format matches expected specification
- No race conditions under concurrent execution

**Remember**: Shell scripting tasks should test understanding of shell quirks (quoting, expansion, subshells) and defensive programming practices. Include edge cases that break naive implementations!
