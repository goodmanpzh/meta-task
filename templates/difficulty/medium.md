**Your task MUST meet ALL of the following criteria to qualify as MEDIUM difficulty:**

**Design Philosophy: Skill Composition and Applied Problem-Solving**
Medium tasks bridge the gap between isolated tool usage (EASY) and deep domain expertise (HARD). They require the agent to combine 2-3 tools or concepts into a coherent solution, make judgment calls about approach, and handle realistic complexity. Think of these as project-style exercises — the kind of task a developer encounters in daily work.

**1. Multi-Tool / Multi-Step Composition**
- The task should require combining at least 2-3 distinct skills or tools
- Examples of skill combinations:
  - Parse a log file (text processing) + aggregate statistics (data processing) + generate a report (file output)
  - Query a database (SQL) + join with a config file (JSON/YAML) + produce filtered output
  - Debug a failing build (read errors) + fix code (programming) + verify the fix (testing)
  - Analyze git history (git log/diff) + extract patterns + modify files accordingly
  - Set up a service (configuration) + send requests to it (HTTP) + validate responses
- No single tool or library call should solve the entire task — the challenge IS the integration

**2. Decision Points and Judgment**
- At least one step should require the agent to choose an approach based on what it discovers
- Include situations where the agent must:
  - Inspect data/files to determine the right processing strategy
  - Handle 2-3 different cases or formats within the same dataset
  - Decide on ordering of operations (some orderings work, others don't)
  - Recover from or work around a minor obstacle (a missing field, a slightly different format)
- The instruction should NOT prescribe the exact sequence of steps — describe the goal and constraints, let the agent figure out the path

**3. Realistic Data with Meaningful Complexity**
- Input data should have realistic scale and structure:
  - Multiple files or a multi-table database, not just one flat file
  - At least 100+ records or equivalent volume
  - Mixed formats that require different handling (e.g., some records have optional fields)
- Include 2-3 legitimate edge cases the agent must handle:
  - Missing or null values that affect computation
  - Duplicate entries that must be deduplicated
  - Cross-references between files that must be resolved
- Edge cases should be discoverable through careful reading, not hidden traps

**4. Multi-Faceted Verification**
- Tests should verify at least 3-4 distinct aspects of the solution:
  - Correctness of the core computation
  - Proper handling of edge cases
  - Output format and structure compliance
  - Completeness (all inputs processed, no records dropped silently)
- At least one test should verify something the agent might overlook if it takes shortcuts
- Tests should be general enough to accept any correct solution approach, not just one specific implementation

**5. Appropriate Scope and Complexity**
- The solution should require 30-120 lines of code or equivalent scripting effort
- The task should involve reading and understanding at least 2-3 provided files
- Should require some exploration of the environment to understand the full picture
- An experienced developer would need to think carefully about the approach but wouldn't need to learn new domain knowledge
- The task should be completable in a focused working session, not require extended research

**Anti-patterns to AVOID:**
- Tasks that are just "EASY but with more data" — medium requires qualitative complexity, not just volume
- Tasks requiring deep domain expertise (compiler passes, crypto primitives, ML architectures) — that's HARD
- Tasks where all steps are obvious from the instruction — medium should require some discovery
- Overly prescriptive instructions that spell out every step — the agent should plan its own approach
- Tasks with only one verification check — medium needs multi-faceted testing
