# Task: Generate a Terminal-Based AI Agent Task

You are an expert in **$category_display** with deep knowledge of best practices, common patterns, and real-world challenges in this domain. Your task is to create a high-quality terminal-based task that tests an AI agent's ability to solve practical problems in a containerized environment.

---

## 1. Reference

To understand what you need to produce, study the following examples in `/app/examples/`:

$example_list
- `/app/examples/_task_template/` — a **skeleton template** with TODO placeholders for each file

**Start by exploring these.** The real example shows the expected format, structure, and quality level. The `_task_template/` is your starting skeleton — copy it to `/app/output/` and fill in the TODO sections.

**Do not imitate the example's content, topic, or problem design.** Create something completely original.

---

## 2. System Architecture

Your generated task is a self-contained package. Here's how it will be used:

```
┌─────────────────────────────────────────────────────────────────┐
│  YOUR CURRENT ENVIRONMENT (where you are now)                   │
│  - You create task files in /app/output/                        │
│  - You can run solve.sh and tests to validate your task         │
│  - You do NOT have Docker permissions here                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Your output files are used to build...
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  AGENT EXECUTION ENVIRONMENT (built from YOUR Dockerfile)       │
│  - Built using: docker build -f environment/Dockerfile          │
│  - The solving agent works here to complete instruction.md      │
│  - Files from environment/ are COPYed into the container        │
│  - Agent has full terminal access but limited time              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ After agent finishes, tests run...
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  TEST VERIFICATION                                              │
│  - tests/ directory is mounted at /tests/                       │
│  - test.sh runs pytest /tests/test_outputs.py                   │
│  - Writes 1 (pass) or 0 (fail) to /logs/verifier/reward.txt    │
└─────────────────────────────────────────────────────────────────┘
```

**The task must be fully self-contained.** A fresh environment is built from your Dockerfile alone. All input data, dependencies, config files, and code referenced in instruction.md must be present inside the built container — either COPYed from `environment/` or generated during `docker build`. Paths in instruction.md, solve.sh, and test_outputs.py must match what actually exists in the container.

---

## 3. Your Output

Generate a **$difficulty** difficulty task. Create all files in `/app/output/`:

```
/app/output/
├── instruction.md          # Your task description (use absolute paths like /app/...)
├── task.toml               # Metadata (version, metadata, verifier, agent, environment)
├── environment/
│   ├── Dockerfile          # FROM, WORKDIR /app, install deps, generate input data
│   └── [data/scripts/...]  # (Optional) Input files, setup scripts, configs
├── solution/
│   └── solve.sh            # #!/bin/bash, reference solution that passes all tests
└── tests/
    ├── test.sh             # Run pytest /tests/test_outputs.py, write 0/1 to /logs/verifier/reward.txt
    └── test_outputs.py     # Pytest tests that verify the solution
```

**File-by-file guidance:**
- `instruction.md` — Write the task description following the Writing Style below; use absolute paths like `/app/...`
- `task.toml` — Fill in difficulty, category, and tags to match your task
- `environment/Dockerfile` — See Dockerfile Best Practices below; all input data must be present after `docker build`
- `solution/solve.sh` — Write the reference solution that proves the task is solvable (not shown to the solving agent)
- `tests/test.sh` — **Use the reward-writing logic from the template as-is** (only modify the `pip install` line to add your test dependencies)
- `tests/test_outputs.py` — Write pytest tests following the rules in the template file header

Note: At runtime, `tests/` is mounted at `/tests/`, so `test.sh` must use `pytest /tests/test_outputs.py`

---

## 4. Task Category (for inspiration)

$category_content

---

## 5. Writing Style for Your instruction.md

$scenario_content

---

## 6. Difficulty Requirements: **$DIFFICULTY**

$difficulty_section

---

## 7. Dockerfile Best Practices

Follow the patterns in the task template (`_task_template/environment/Dockerfile`). Key rules:

- **NEVER use heredoc syntax** (`<< EOF`) — it causes Docker build failure. Use `printf`, `echo`, `python3 -c`, or COPY a file instead.
- **NEVER COPY solution/ or tests/ into the image** — they are mounted at runtime, not baked into the container.
- **Verify every COPY source** exists under `environment/` before finalizing.
- **Pin dependency versions** when stability matters: `pip install numpy==1.24.0`
- **Delete setup scripts after execution**: `RUN bash setup.sh && rm setup.sh`
- **Required base**: `FROM python:3.11-slim`, `WORKDIR /app`, install `procps`

---

## 8. Recommended Workflow

Follow this sequence — **do NOT skip the exploration and design phases**:

1. **Explore** — Study the reference example and task template to understand expected format and quality. Review the Task Category section for inspiration.
2. **Design** — Think carefully about what problem to create. Consider: What makes this problem interesting and genuinely challenging? How do instruction, environment, solution, and tests fit together as a self-contained whole? Plan the relationships between components before writing any files.
3. **Implement** — Copy `/app/examples/_task_template/` to `/app/output/` and fill in each component.
4. **Validate** — Run solve.sh, then run tests, then check cross-component consistency (see Self-Validation below). Fix any issues and repeat.
5. **Clean up** — Remove validation artifacts.

---

## 9. Self-Validation (REQUIRED)

**Before finishing, you MUST validate your task is solvable and consistent:**

**Step 1: Execute your solution**
```bash
bash /app/output/solution/solve.sh
```

**Step 2: Run tests to verify**
```bash
pytest /app/output/tests/test_outputs.py -v
```

**Step 3: Verify consistency across all components**

| Check | Question to Ask |
|-------|-----------------|
| **instruction ↔ solution** | Does solve.sh actually accomplish what instruction.md asks? |
| **instruction ↔ environment** | Does Dockerfile provide all files/tools mentioned in instruction? |
| **solution ↔ tests** | Does solve.sh output match exactly what tests expect (paths, formats, values)? |
| **tests ↔ instruction** | Bidirectional: every test traces back to a requirement in instruction.md, and every requirement in instruction.md has a corresponding test. Any correct solution should pass, not just your specific solve.sh. |
| **instruction specifies output** | Does instruction.md explicitly define the expected output format (file paths, JSON field names, data structure, etc.)? All paths must be absolute (e.g., `/app/output/result.json`). The solving agent should not have to guess. |
| **tests are robust** | Tests must verify behavior through execution (run code, check results), not just string matching or grep on file contents. Avoid failing on trailing whitespace, newline differences, or minor stylistic variations. |

**Step 4: If any test fails or consistency check fails, fix and repeat from Step 1**

**Step 5: Clean up** — Remove any output files created during validation

---

## 10. Final Checklist

- [ ] **All files present**: `/app/output/` contains all 6 required files: `instruction.md`, `task.toml`, `environment/Dockerfile`, `solution/solve.sh`, `tests/test.sh`, `tests/test_outputs.py`
- [ ] **Solvability**: solve.sh runs successfully and produces correct output
- [ ] **Tests pass**: `pytest test_outputs.py -v` shows all tests green
- [ ] **Tests are general**: Any correct solution to instruction.md should pass tests, not just your specific solve.sh
- [ ] **Output format documented**: instruction.md explicitly specifies output file paths, data formats, and field names that tests check for
- [ ] **Self-contained**: All paths, data, and dependencies exist inside the built container
- [ ] **Consistency**: instruction ↔ solution ↔ tests ↔ environment all correctly aligned
- [ ] **Originality**: Task is genuinely different from examples
- [ ] **Dockerfile**: No heredoc syntax, valid packages, all COPY sources exist
- [ ] **No answer leakage**: Environment files don't contain solutions; instruction describes WHAT not HOW
- [ ] **Test dependencies**: test.sh installs all packages imported by test_outputs.py
- [ ] **Difficulty**: Task genuinely meets **$DIFFICULTY** criteria
- [ ] **Clean state**: Removed output files created during validation
