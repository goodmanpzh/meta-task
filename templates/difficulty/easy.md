**Your task MUST meet ALL of the following criteria to qualify as EASY difficulty:**

**Design Philosophy: Foundational Tool Mastery**
Easy tasks are NOT trivial one-liners. They are structured exercises that teach an AI agent to correctly use fundamental terminal tools, file formats, and programming patterns. Think of these as textbook exercises — focused on a single skill, but requiring a complete workflow (read input → apply tool/technique → produce verified output).

**1. Single Core Skill Focus**
- Each task should exercise ONE primary tool or technique thoroughly
- Examples of core skills to train:
  - File manipulation: `sed`, `awk`, `grep`, `sort`, `cut`, `jq`, `xargs`
  - Text processing: regex, encoding/decoding (base64, hex, URL-encoding), character set conversion
  - Data formats: JSON, CSV, YAML, TOML, INI — parsing, transforming, validating
  - Shell fundamentals: pipes, redirection, process substitution, exit codes, signal handling
  - Git basics: branching, merging, cherry-pick, log filtering, diff interpretation
  - Python stdlib: `os`, `pathlib`, `json`, `csv`, `re`, `sqlite3`, `argparse`, `collections`
  - System inspection: `ps`, `lsof`, `df`, `du`, `find`, `stat`, `file`, `xxd`
  - Network basics: `curl`, `wget`, HTTP methods, status codes, headers
- The agent should learn to use the tool correctly, not just get the right answer by accident

**2. Clear and Complete Workflow**
- The task must have a well-defined input → processing → output pipeline
- Provide concrete input data in the environment (not just "create your own")
- Specify the exact output format and location (e.g., "write results to /app/output/result.txt, one item per line, sorted alphabetically")
- The task should require 5-15 meaningful commands or 20-60 lines of scripting to solve
- Should NOT be solvable with a single command, but should NOT require more than one file of code

**3. Realistic but Controlled Input Data**
- Input data should be realistic enough to be meaningful (not `foo`, `bar`, `baz`)
- Include enough data points to prevent manual/hardcoded solutions (e.g., 50+ records, not 3)
- Include minor "real-world noise" that the agent must handle correctly:
  - Trailing whitespace, mixed line endings, empty lines in CSVs
  - Unicode characters in otherwise ASCII text
  - Optional fields or slightly inconsistent formatting
- But NO deliberate traps or adversarial edge cases — the noise is incidental, not the point

**4. Verification That Teaches Correctness**
- Tests should verify the output is exactly correct, not just approximately right
- Prefer deterministic checks: exact file contents, sorted output, specific counts
- Include 2-3 test assertions that cover:
  - Basic correctness (did the transformation work?)
  - Completeness (did you process ALL records, not just some?)
  - Format compliance (correct delimiter, encoding, line endings?)

**5. What Makes This EASY (Not Trivial)**
- The agent should need to READ and UNDERSTAND the input data before processing
- The task should require choosing the right tool/approach (not told "use awk to...")
- The instruction describes WHAT to achieve, not HOW to achieve it
- A competent developer would solve this confidently but still needs to think briefly about approach

**Anti-patterns to AVOID:**
- "Install package X and run hello world" — no learning value
- Tasks solvable with a single `cat | grep | sort` pipeline — too trivial
- Tasks requiring domain expertise (cryptography, ML, compiler theory) — that's HARD territory
- Ambiguous output formats ("summarize the data") — easy tasks need precise specifications
- Tasks with no input data ("create a script that...") — always provide concrete data to work with
