#!/usr/bin/env python3
"""
Quality Gate: LLM-based task quality and answer-leakage reviewer.

Scans generated tasks, constructs review prompts with all relevant task files,
calls an LLM to evaluate quality and detect answer leakage, and produces
a report with pass/fail results.

Usage:
    python quality_gate.py --source /path/to/tasks/ --report /path/to/report.json
    python quality_gate.py --source /path/to/tasks/ --output /path/to/filtered/ --report report.json
    python quality_gate.py --source /path/to/tasks/ --report report.json --workers 5
"""

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Optional

import litellm

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_API_BASE = ""  # Set via --api-base or the API_BASE env var (e.g. http://localhost:8000/v1)
DEFAULT_API_KEY = "EMPTY"
DEFAULT_MODEL = ""  # Set via --model (e.g. the served model name of your vLLM/OpenAI-compatible endpoint)
DEFAULT_WORKERS = 5
DEFAULT_RETRIES = 3
DEFAULT_SLEEP = 2
DEFAULT_MAX_TOKENS = 16384

# Files to always include (if they exist)
CORE_FILES = [
    "instruction.md",
    "task.toml",
    "environment/Dockerfile",
    "solution/solve.sh",
    "tests/test.sh",
    "tests/test_outputs.py",
    "tests/test_state.py",
]

# Max file size to include in prompt (characters)
MAX_FILE_SIZE = 50000
# Max total prompt size (characters)
MAX_PROMPT_SIZE = 120000

# ---------------------------------------------------------------------------
# Review Prompt
# ---------------------------------------------------------------------------
REVIEW_SYSTEM_PROMPT = """\
You are a benchmark task quality auditor for terminal-based AI agent evaluation tasks.

## How This Benchmark Works

Each task is a challenge for an AI agent. The execution flow is:

1. A Docker container is BUILT from environment/Dockerfile
2. The AI agent is placed INSIDE this container with only instruction.md visible
3. The agent uses the terminal (bash) to explore, write code, and produce the required output
4. After the agent finishes (or times out), tests/ is mounted and test.sh runs to verify
5. The agent gets reward=1 (pass) or reward=0 (fail)

## What the Agent CAN and CANNOT See

CAN see (inside the running container):
- instruction.md (the task description)
- Everything the Dockerfile put into the image: installed packages, COPY'd files, files created by RUN commands that were NOT deleted
- The agent has full root access, can run any command, read any file in the container

CANNOT see:
- solution/ directory — this is the reference answer, only used by the oracle test runner, NEVER inside the container
- tests/ directory — only mounted AFTER the agent finishes, the agent never sees the test logic

## Key Technical Detail About Dockerfiles

When you see: `RUN python3 /tmp/script.py && rm /tmp/script.py`
- The script executes and then is DELETED in the same layer
- The script is NOT accessible in the final container
- But any FILES the script CREATED (that are not also deleted) DO remain accessible
- Example: if script.py writes /app/data/output.json, that file persists even though script.py itself is gone

## What Makes a Task BAD

A task is unacceptable if the agent can achieve the correct output WITHOUT doing the intended intellectual work. This includes:

1. **Answer files left in container**: ground_truth.json, expected.json, metadata with answers, etc.
2. **Complete solution code in container**: A working script the agent just needs to run
3. **Data that directly reveals answers**: Labels, classifications, flags in the input data that should be discovered
4. **Bug comments that eliminate diagnosis**: "# BUG: should use X instead of Y" makes debugging trivial
5. **Instruction that describes the solution**: Step-by-step fix instructions instead of just the goal
"""

REVIEW_USER_PROMPT_TEMPLATE = """\
Review this task for quality issues. All task files are shown below.

{task_files_section}

---

## Analysis Steps

### Step 1: Trace the Dockerfile to determine the final container state

Read the Dockerfile carefully and determine:
- What files are COPY'd into the container?
- What RUN commands execute scripts? Are those scripts deleted afterwards (look for "&& rm" in the SAME RUN line)?
- What OUTPUT files do the scripts create that remain in the container?
- Final answer: list ALL files the agent can access when it starts working.

### Step 2: Check for answer leakage in accessible files

For each file accessible in the container (from Step 1), check:
- Does it contain pre-computed answers that the agent is supposed to derive through its own work?
- Does it contain classification labels or boolean flags that directly reveal what the agent should discover?
- Is it a complete, working script that produces the expected output when run?
- Does it contain the exact values the tests check against?

Note: if a generate/setup script is provided in environment/, even if it gets deleted after execution, you should read its source and trace what files it writes into the container — those output files persist and may contain answers.

### Step 3: Check for difficulty-destroying information

Even without explicit answer files, check:
- Do source code files have "# BUG:" comments that pinpoint issues AND describe the fix?
- Does instruction.md list the exact bugs/problems AND their solutions?
- Can the agent solve the task by simple grep + mechanical fix rather than actual reasoning?
- Is the task so over-specified that no exploration or thinking is required?

### Step 4: Assess overall quality

- Is the task self-consistent? (instruction asks for X, tests verify X, solution produces X)
- Is the instruction appropriately concise? (not a step-by-step tutorial)
- Do tests verify meaningful behavior through execution, not just string matching?
- Does the task require genuine multi-step reasoning and implementation?

---

## IMPORTANT REMINDERS

- A script being COPY'd into the Dockerfile does NOT mean it's accessible — check if it's deleted with "rm" in the same RUN line.
- solution/solve.sh containing the full answer is NORMAL — the agent never sees it.
- tests/test_outputs.py referencing expected values is NORMAL — the agent never sees it.
- Data generation scripts being deleted is the CORRECT pattern. Focus on what OUTPUT they leave behind.
- "leaked" means the agent can access the answer from WITHIN the container. Not that the answer exists somewhere in the task package.

---

Respond in the following JSON format ONLY (no other text outside the JSON block):
```json
{{
  "accessible_files": ["list the key files accessible to the agent in the container"],
  "leaked": true/false,
  "leak_type": "none" | "solution_in_image" | "answer_in_data" | "output_precomputed" | "trivial_shortcut" | "bug_comments_reveal_fix" | "multiple",
  "leak_details": "specific file path and content that leaks the answer, or null if no leak",
  "severity": "critical" | "high" | "medium" | "low" | "none",
  "quality_score": 1-5,
  "quality_issues": ["list of specific quality issues found"],
  "true_difficulty": "trivial" | "easy" | "medium" | "hard" | "extreme",
  "recommendation": "pass" | "fail",
  "explanation": "brief overall assessment in 1-2 sentences"
}}
```
"""


# ---------------------------------------------------------------------------
# Task discovery and file reading
# ---------------------------------------------------------------------------
def discover_tasks(source_dir: str) -> list:
    """Find all task subdirectories containing instruction.md."""
    tasks = []
    source_path = Path(source_dir)
    if not source_path.is_dir():
        print(f"Error: {source_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    for entry in sorted(source_path.iterdir()):
        if entry.is_dir() and (entry / "instruction.md").is_file():
            tasks.append({"task_name": entry.name, "task_dir": str(entry)})

    return tasks


def read_file_safe(filepath: str, max_size: int = MAX_FILE_SIZE) -> Optional[str]:
    """Read a file safely, truncating if too large."""
    try:
        with open(filepath, encoding="utf-8", errors="replace") as f:
            content = f.read(max_size)
            if len(content) >= max_size:
                content += "\n... [TRUNCATED]"
            return content
    except (OSError, IOError):
        return None


# Binary file extensions to skip (not useful for LLM review)
BINARY_EXTENSIONS = {
    ".pkl", ".npy", ".npz", ".h5", ".hdf5", ".sqlite", ".db",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
    ".bin", ".dat", ".so", ".o", ".a", ".dylib",
    ".pyc", ".pyo", ".whl", ".egg",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".mp3", ".mp4", ".wav", ".avi",
    ".ttf", ".otf", ".woff",
}


def collect_environment_files(task_dir: str) -> list:
    """Collect all files in environment/ (excluding Dockerfile and binary files)."""
    env_dir = Path(task_dir) / "environment"
    if not env_dir.is_dir():
        return []

    files = []
    for filepath in sorted(env_dir.rglob("*")):
        if filepath.is_file() and filepath.name != "Dockerfile":
            if filepath.suffix.lower() not in BINARY_EXTENSIONS:
                rel_path = filepath.relative_to(Path(task_dir))
                files.append(str(rel_path))
    return files




# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------
def build_review_prompt(task_dir: str) -> str:
    """Build the review prompt for a single task."""
    sections = []

    # Core files
    for relpath in CORE_FILES:
        filepath = os.path.join(task_dir, relpath)
        if os.path.isfile(filepath):
            content = read_file_safe(filepath)
            if content:
                sections.append(f"=== {relpath} ===\n{content}")

    # Additional environment files (non-Dockerfile)
    env_files = collect_environment_files(task_dir)
    for relpath in env_files:
        filepath = os.path.join(task_dir, relpath)
        content = read_file_safe(filepath)
        if content:
            sections.append(f"=== {relpath} ===\n{content}")

    # Additional solution files (beyond solve.sh)
    sol_dir = Path(task_dir) / "solution"
    if sol_dir.is_dir():
        for filepath in sorted(sol_dir.rglob("*")):
            if filepath.is_file() and filepath.name != "solve.sh":
                rel_path = filepath.relative_to(Path(task_dir))
                content = read_file_safe(str(filepath))
                if content:
                    sections.append(f"=== {rel_path} ===\n{content}")

    task_files_section = "\n\n".join(sections)

    # Truncate if total prompt is too large
    if len(task_files_section) > MAX_PROMPT_SIZE:
        task_files_section = task_files_section[:MAX_PROMPT_SIZE] + "\n\n... [CONTENT TRUNCATED]"

    return REVIEW_USER_PROMPT_TEMPLATE.format(task_files_section=task_files_section)


# ---------------------------------------------------------------------------
# LLM calling
# ---------------------------------------------------------------------------
def call_llm(
    prompt: str,
    api_base: str,
    api_key: str,
    model: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    retries: int = DEFAULT_RETRIES,
    sleep: float = DEFAULT_SLEEP,
) -> Optional[str]:
    """Call the LLM API via litellm and return the response text."""
    messages = [
        {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    for attempt in range(retries):
        try:
            resp = litellm.completion(
                model=model,
                api_base=api_base,
                api_key=api_key,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.8,
                extra_body={
                    "top_k": 20,
                    "chat_template_kwargs": {"enable_thinking": False},
                },
            )
            return resp.choices[0].message.content
        except Exception as e:
            if attempt < retries - 1:
                print(f"  Retry {attempt + 1}/{retries}: {e}", file=sys.stderr)
                time.sleep(sleep * (attempt + 1))
            else:
                print(f"  Failed after {retries} retries: {e}", file=sys.stderr)
                return None


def parse_llm_response(response: str) -> Optional[dict]:
    """Parse the JSON response from the LLM."""
    if not response:
        return None

    # Try to find JSON in the response
    # First try: look for ```json ... ``` block
    json_match = re.search(r"```json\s*\n?(.*?)\n?```", response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Second try: find first { ... } block
    brace_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    # Third try: parse the whole response
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Review worker
# ---------------------------------------------------------------------------
def review_task(
    task: dict,
    api_base: str,
    api_key: str,
    model: str,
    max_tokens: int,
    retries: int,
    sleep: float,
) -> dict:
    """Review a single task and return the result."""
    task_name = task["task_name"]
    task_dir = task["task_dir"]

    prompt = build_review_prompt(task_dir)
    response = call_llm(prompt, api_base, api_key, model, max_tokens, retries, sleep)
    parsed = parse_llm_response(response)

    result = {
        "task_name": task_name,
        "raw_response": response,
        "parsed": parsed,
    }

    if parsed:
        result["leaked"] = parsed.get("leaked", False)
        result["recommendation"] = parsed.get("recommendation", "fail")
        result["quality_score"] = parsed.get("quality_score", 0)
        result["leak_type"] = parsed.get("leak_type", "unknown")
        result["severity"] = parsed.get("severity", "unknown")
        result["true_difficulty"] = parsed.get("true_difficulty", "unknown")
    else:
        result["leaked"] = None
        result["recommendation"] = "fail"
        result["quality_score"] = 0
        result["parse_error"] = True

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Quality Gate: LLM-based task quality and answer-leakage reviewer"
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Directory containing task subdirectories",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Directory to copy passed tasks to (optional, if not set only report is generated)",
    )
    parser.add_argument(
        "--report",
        type=str,
        default="quality_gate_report.json",
        help="Path to write the JSON report (default: quality_gate_report.json)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Model name (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--api-base",
        type=str,
        default=DEFAULT_API_BASE,
        help=f"API base URL (default: {DEFAULT_API_BASE})",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=DEFAULT_API_KEY,
        help=f"API key (default: {DEFAULT_API_KEY})",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help=f"Number of parallel workers (default: {DEFAULT_WORKERS})",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Number of retries per request (default: {DEFAULT_RETRIES})",
    )
    parser.add_argument(
        "--sleep",
        type=float,
        default=DEFAULT_SLEEP,
        help=f"Sleep between retries in seconds (default: {DEFAULT_SLEEP})",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help=f"Max tokens for LLM response (default: {DEFAULT_MAX_TOKENS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only discover tasks and print prompts, don't call LLM",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit number of tasks to review (0 = all)",
    )
    args = parser.parse_args()

    # Discover tasks
    tasks = discover_tasks(args.source)
    if not tasks:
        print("No tasks found. Exiting.", file=sys.stderr)
        sys.exit(1)

    if args.limit > 0:
        tasks = tasks[: args.limit]

    print(f"Found {len(tasks)} task(s) in {args.source}")

    # Dry run mode
    if args.dry_run:
        for task in tasks[:3]:
            prompt = build_review_prompt(task["task_dir"])
            print(f"\n{'='*60}")
            print(f"Task: {task['task_name']}")
            print(f"Prompt length: {len(prompt)} chars")
            print(f"{'='*60}")
            print(prompt[:3000])
            print("...")
        return

    # Review tasks
    results = []
    lock = Lock()
    completed_count = [0]

    def worker(task):
        result = review_task(
            task,
            args.api_base,
            args.api_key,
            args.model,
            args.max_tokens,
            args.retries,
            args.sleep,
        )
        with lock:
            completed_count[0] += 1
            status = "LEAK" if result.get("leaked") else "OK"
            rec = result.get("recommendation", "?")
            score = result.get("quality_score", "?")
            print(
                f"  [{completed_count[0]}/{len(tasks)}] {task['task_name']}: "
                f"{status} | rec={rec} | quality={score}"
            )
        return result

    print(f"\nReviewing with model={args.model}, workers={args.workers}...")
    print("-" * 60)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(worker, task): task for task in tasks}
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                task = futures[future]
                print(f"  ERROR: {task['task_name']}: {e}", file=sys.stderr)
                results.append(
                    {
                        "task_name": task["task_name"],
                        "error": str(e),
                        "recommendation": "fail",
                    }
                )

    # Sort results by task name
    results.sort(key=lambda r: r.get("task_name", ""))

    # Generate summary
    total = len(results)
    passed = sum(1 for r in results if r.get("recommendation") == "pass")
    failed = sum(1 for r in results if r.get("recommendation") == "fail")
    leaked = sum(1 for r in results if r.get("leaked") is True)
    parse_errors = sum(1 for r in results if r.get("parse_error"))

    summary = {
        "total": total,
        "passed": passed,
        "failed": failed,
        "leaked_count": leaked,
        "parse_errors": parse_errors,
        "model": args.model,
        "source": args.source,
    }

    # Print summary
    print("\n" + "=" * 60)
    print("QUALITY GATE SUMMARY")
    print("=" * 60)
    print(f"  Total tasks:    {total}")
    print(f"  Passed:         {passed}")
    print(f"  Failed:         {failed}")
    print(f"  Leaked:         {leaked}")
    print(f"  Parse errors:   {parse_errors}")
    print("=" * 60)

    # Print failed tasks
    if failed > 0 or leaked > 0:
        print("\nFAILED / LEAKED TASKS:")
        for r in results:
            if r.get("recommendation") == "fail" or r.get("leaked"):
                leak_type = r.get("leak_type", "?")
                severity = r.get("severity", "?")
                details = ""
                if r.get("parsed"):
                    details = r["parsed"].get("leak_details", "") or ""
                print(f"  - {r['task_name']}: type={leak_type}, severity={severity}")
                if details:
                    print(f"    {details[:200]}")

    # Write report
    report = {"summary": summary, "results": []}
    for r in results:
        entry = {
            "task_name": r.get("task_name"),
            "leaked": r.get("leaked"),
            "recommendation": r.get("recommendation"),
            "quality_score": r.get("quality_score"),
            "leak_type": r.get("leak_type"),
            "severity": r.get("severity"),
            "true_difficulty": r.get("true_difficulty"),
        }
        if r.get("parsed"):
            entry["quality_issues"] = r["parsed"].get("quality_issues", [])
            entry["explanation"] = r["parsed"].get("explanation", "")
            entry["leak_details"] = r["parsed"].get("leak_details")
        if r.get("error"):
            entry["error"] = r["error"]
        report["results"].append(entry)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport saved to {report_path}")

    # Copy passed tasks to output directory
    if args.output:
        import shutil

        output_path = Path(args.output)
        output_path.mkdir(parents=True, exist_ok=True)
        copied = 0
        for r in results:
            if r.get("recommendation") == "pass":
                src = Path(args.source) / r["task_name"]
                dst = output_path / r["task_name"]
                if src.is_dir():
                    if dst.exists():
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                    copied += 1
        print(f"Copied {copied} passed tasks to {args.output}")


if __name__ == "__main__":
    main()
