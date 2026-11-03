**Your task MUST meet ALL of the following criteria to qualify as HARD difficulty:**

**1. Specialized Knowledge Required**
- The task must require domain expertise that goes beyond basic programming
- Examples: cryptographic algorithms, compiler internals, signal processing, bioinformatics, reverse engineering
- A general-purpose developer should NOT be able to solve it without learning new concepts

**2. Non-Obvious Solution Path**
- The solution must NOT be a straightforward "read input → process → write output" pipeline
- Require creative problem-solving, algorithm design, or reverse engineering
- Include at least one step where the solver must discover or infer something not explicitly stated
- The agent must explore the environment (read files, inspect configs, understand code) before knowing how to proceed

**3. Difficulty from the Materials, Not Artificial Constraints**
- The challenge should come from the inherent complexity of the real materials — understanding a real codebase, parsing a real data format, building on top of a real system
- Do NOT make tasks hard by just adding arbitrary time limits or format restrictions on top of a simple problem
- Good difficulty: "implement a compatible extension for this real C++ project by reading its custom allocator source and internal APIs"
- Bad difficulty: "parse this CSV but you must do it in under 2 seconds" (artificial constraint on a simple task)

**4. Multi-Stage Verification**
- Tests must verify multiple intermediate or final artifacts (not just one output file)
- Include at least 3 distinct verification checks
- Verify both correctness AND constraints (performance, size, format)

**5. Real-World Complexity**
- Model realistic scenarios with edge cases and error conditions
- Include at least one "trap" that a naive implementation would fail on
- The task should require multiple rounds of exploration, trial-and-error, or iterative refinement to solve
- The task should take an expert 30+ minutes to solve

**Anti-patterns to AVOID:**
- Simple CRUD operations on well-documented formats
- Tasks solvable with a single library call
- Problems with obvious, linear solutions
- Basic ML training (MNIST-level tasks)
- Simple encryption/decryption with known algorithms
- Making a simple task "hard" by adding artificial constraints (time limits, format restrictions)