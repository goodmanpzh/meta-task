**Before designing the task, think holistically:** consider what combination of skills, tools, and knowledge the solving agent will need. An extreme task should require the agent to explore the environment across multiple rounds, form hypotheses, test them, adjust its approach, and iterate — not solve in a single linear pass. Plan your task so that different phases of the solution demand different capabilities.

**Your task MUST meet ALL of the following criteria to qualify as EXTREME difficulty:**

**1. Deep Domain Expertise Required**
- The task requires knowledge that even experienced developers in related fields would need to research
- The solver must study the provided materials (source code, documentation, data formats) to gain the necessary understanding — the knowledge is NOT something an LLM would have memorized from training
- Examples: implementing a custom memory allocator by studying an existing runtime's internals, reverse-engineering an undocumented binary protocol from packet captures, implementing a differential cryptanalysis attack by studying a specific cipher implementation

**2. Discovery-Driven Problem Solving**
- The problem statement alone is NOT sufficient to solve the task — the agent must explore the environment extensively
- Critical information is embedded in the materials: buried in source code comments, encoded in data patterns, implied by configuration, or only revealed through running and observing the system
- The agent must form and test hypotheses, not just follow instructions
- Example: "build a compatible implementation" — the agent must understand the existing system's architecture, figure out which interfaces to implement, and produce working code that integrates correctly

**3. Multi-Step Reasoning Chain**
- The solution requires chaining together 3+ non-obvious insights, where each insight depends on the previous one
- No single step is trivial — each requires understanding a different aspect of the materials
- Different steps should draw on different skills and tools available in the terminal environment
- The agent cannot brute-force the solution; it must understand the underlying system

**4. Materials ARE the Challenge**
- The difficulty comes directly from the complexity of the real-world materials, not from artificial constraints
- The materials should contain enough complexity that the agent must invest significant effort just to understand them before attempting a solution
- Examples: a real codebase with 10+ files where the implementation spans multiple modules, a real dataset with undocumented schema that must be reverse-engineered, a real system with interacting components where the agent must build a new feature that integrates correctly

**5. Expert-Level Verification**
- Tests must verify deep correctness, not just surface-level output
- Include at least 5 distinct verification checks
- Verify that the solution demonstrates actual understanding (not just pattern-matching the expected output)
- Include edge cases that only a correct implementation would handle

**6. Time and Complexity**
- The task should take a domain expert 60+ minutes to solve
- A strong AI agent should need multiple rounds of exploration, hypothesis testing, and iterative refinement
- The solution path involves repeated cycles: try something, observe the result, adjust the approach, try again — not a single linear execution
- First-attempt solutions should almost certainly fail — the task rewards persistence and systematic problem-solving

**7. Difficulty Self-Check (MANDATORY after generating the task)**

After generating your task, verify it against each criterion above. If any check fails, you MUST redesign the task to increase difficulty.

- Re-read instruction.md alone: could a skilled developer sketch the solution approach within 5 minutes? If yes → task is NOT extreme. Redesign so the approach can only be discovered through exploring the environment.
- Count environment files that the agent MUST read to solve the task. If fewer than 5 → add more complexity to the materials.
- List the non-obvious insights required. If you cannot identify 3+ → the task is too straightforward. Add layers of complexity.
- Check if your instruction describes the output schema, names the algorithms, or provides step-by-step guidance. If yes → you have leaked the solution into the instruction. Make the instruction shorter and vaguer.
- Ask: would a first attempt (the "obvious" approach) succeed? If yes → add constraints or hidden requirements that make naive approaches fail.

If your task does not pass ALL checks above, iterate on the design until it does.

**Anti-patterns to AVOID:**
- Tasks that are merely "hard" versions of simple tasks (more data, tighter time limits)
- Tasks where reading the instruction is sufficient to know the solution approach
- Tasks where the materials are just "context" but the actual problem is straightforward
- Tasks solvable by copying code from Stack Overflow or common tutorials
- Difficulty through obscurity (hiding information in weird places) rather than genuine complexity
- Instructions that are too long or too detailed — extreme tasks have short instructions and deep environments
