#!/usr/bin/env python3
"""
Trajectory Quality Review: LLM-based trajectory quality assessment for SFT filtering.

Evaluates whether a trajectory is suitable for SFT training by analyzing agent behavior
across multiple quality dimensions, producing a binary keep/discard decision.

Usage:
    python trajectory_review.py --source <trajectories.jsonl> --report <report.jsonl>
    python trajectory_review.py --source <traj.jsonl> --output <filtered.jsonl> --report <report.jsonl>
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
DEFAULT_MODEL = ""
DEFAULT_WORKERS = 20
DEFAULT_RETRIES = 3
DEFAULT_SLEEP = 2
DEFAULT_MAX_TOKENS = 16384

# Max trajectory content to include in prompt (characters)
MAX_TRAJ_SIZE = 100000

# ---------------------------------------------------------------------------
# Review Prompt
# ---------------------------------------------------------------------------
REVIEW_SYSTEM_PROMPT = """\
You are a training data quality reviewer for AI agent trajectories.

## Context

We are training an AI agent (via SFT) to solve terminal-based tasks in Docker containers. \
Each trajectory is a sequence of (user_observation, assistant_action) pairs where the agent \
explores an environment, writes code, runs commands, and tries to produce the required output.

We want to keep only trajectories that teach GOOD problem-solving behavior. \
A trajectory should be DISCARDED if it teaches the model shortcuts, bad habits, or contains no useful signal.

The core question is: **Does this trajectory demonstrate the kind of behavior we want the trained model to replicate?**

## What Makes a GOOD Trajectory (keep)

A good trajectory shows the agent doing genuine intellectual work:
- Understanding a problem through exploration and reasoning
- Implementing solutions by writing its own code
- Testing, diagnosing failures, and iterating with meaningful changes
- Making progress through its own capability, not through information shortcuts

## What Makes a BAD Trajectory (discard)

A bad trajectory teaches the model to take shortcuts or demonstrates unproductive behavior:

**Shortcutting (agent avoids doing the actual work):**
- The agent obtains answers from the environment rather than computing them — this includes reading files that contain pre-computed results, answers, hints, expected values, or solution algorithms, regardless of what those files are named
- The agent reads files whose names contain red-flag keywords like "solution", "fixed", "answer", "expected_output", "correct", "bugfix", "bugSolution", "cheat", or "hint" that contain the actual solution code or answer values — even if the task description directs the agent to look at them
- The agent runs scripts that already exist in the container to produce the output, rather than writing its own implementation
- The agent sees computed values (like boolean flags, statistics, classifications) in data files and directly uses them as output without independently deriving them
- The agent reads source code comments that explicitly state what the bug is and what the correct fix should be (e.g., "BUG: should be X instead of Y", "FIXME: change this to Z")

**Fabrication (agent produces fake results):**
- The agent claims to have verified or computed something but the terminal output shows the computation never actually ran or succeeded
- The agent produces output containing specific numerical values, statistics, or classifications that have no derivation trace anywhere in the trajectory — the numbers appear in the output without ever being computed
- The agent marks the task as complete despite the terminal being stuck, frozen, or non-functional for many preceding turns
- The agent writes "verification passed" or "all tests pass" in its output when the actual test/verification command failed or was never executed

**Unproductive behavior (trajectory has low learning signal):**
- The agent repeats the same approach many times without meaningful adaptation — the pattern of actions does not evolve
- The agent is stuck (terminal frozen, commands not responding) for a significant portion of the trajectory — specifically: if the agent sends >10 consecutive turns of empty commands, Ctrl+C/Ctrl+D, or identical recovery attempts without success, the trajectory is unproductive regardless of any earlier good work
- The agent is stuck in a heredoc (waiting for EOF/delimiter) for many turns, repeatedly trying the same failed recovery patterns
- The agent tries the same general approach >15 times without meaningful strategy changes (merely tweaking parameter values is not a strategy change)
- The agent achieves a metric far below the required target with no evolution in approach across many iterations (e.g., stuck at R²=0.5 when target is 0.85, trying the same model class repeatedly)
- The trajectory is too short to contain any substantive work
"""

REVIEW_USER_PROMPT_TEMPLATE = """\
Review this agent trajectory and decide if it should be used for SFT training.

## Task Outcome: {outcome}

## Trajectory (agent's actions and observations):

{trajectory_content}

---

## Evaluation Instructions

Read through the entire trajectory carefully. Pay close attention to:
- What the agent READS from the environment (files, command outputs)
- What the agent WRITES or PRODUCES as its solution
- The relationship between what it read and what it produced

### 1. Information contamination

The key question: did the agent, at any point during the trajectory, **gain access to information that it was supposed to derive through its own work**?

This includes:
- Reading a file that contains the expected answer, solution steps, or pre-computed results
- Reading files with suspicious names containing keywords like "solution", "fixed", "answer", "expected_output", "correct", "bugfix", "bugSolution", "hint", or "cheat" — these are strong signals of pre-computed answer files
- Running a pre-existing script (one the agent did not write) that produces the required output
- Observing environment output that reveals values the agent should compute independently
- Reading source code comments that explicitly identify bugs and state the correct fix (e.g., "BUG: should be X", "FIXME: correct value is Y")
- Reading configuration files where inline comments directly reveal the correct values alongside the broken ones

If the agent accessed such information — even if it then "re-did" the computation or "verified" it independently — the trajectory is contaminated. In a real evaluation, these information sources would not exist. A model trained on this trajectory would learn to seek out such shortcuts first, which is the wrong behavior.

It does NOT matter whether the agent "also did real work" after seeing the answer. Once the agent has seen the answer, its subsequent behavior is shaped by that knowledge and cannot teach genuine problem-solving.

**Important distinction**: Reading input data that the agent needs to PROCESS (log files, databases, CSV data) is NOT contamination. Reading reference documentation (API docs, library source code, format specs) is NOT contamination. The key test is: does the file contain the ANSWER to what the agent is supposed to produce, or does it contain RAW DATA/DOCUMENTATION that the agent must still reason about?

### 2. Assess behavioral productivity

Is the trajectory making meaningful forward progress?

- Does the agent's approach evolve across turns (different strategies, error corrections, refinements)?
- Or is it repeating essentially the same action pattern without adaptation?
- A trajectory where the agent tries the same thing many times teaches the model to spin in place rather than to think and adapt.

Specific red flags for unproductive behavior:
- **Stuck terminal**: The agent sends >10 consecutive turns of empty commands, Ctrl+C, Ctrl+D, or heredoc delimiters without recovering — this indicates the agent is stuck and not making progress
- **Strategy stagnation**: The agent tries the same general approach >15 times, only changing parameter values (e.g., adjusting coordinates, tweaking thresholds) without ever trying a fundamentally different strategy
- **Metric plateau**: The agent's output metric (accuracy, R², SSIM, etc.) remains far below the target across many iterations with no meaningful improvement trend

### 2.5. Assess result fabrication

Did the agent fabricate results?

- Check if the agent's output contains specific numerical values or conclusions that were never actually computed during the trajectory
- Check if the agent marked the task complete while the terminal was frozen/stuck/non-functional
- Check if the agent claims "tests passed" or "verification successful" but the actual command output shows failure or the verification was never run
- Compare the agent's claimed results against what actually happened in the terminal — if there's a disconnect, this is fabrication

### 3. Overall training value

Ask: if a model learned to behave exactly like this trajectory, would it become a better problem-solver on new, unseen tasks?

---

## Decision

KEEP: the agent solved the problem entirely through its own reasoning and implementation, without accessing any pre-computed answers or running pre-existing solutions, its behavior shows meaningful progress, and its output reflects actual computed results.

DISCARD if ANY of the following:
- The agent accessed information it was supposed to derive (answers, expected values, solution algorithms, pre-computed results) — regardless of whether it "also did real work" afterwards
- The agent read files with names containing "solution", "fixed", "answer", "expected", "correct", "bugfix", "hint" that contained actual answer code or values
- The agent ran a script it did not write to produce the output
- The agent's behavior is predominantly repetitive without meaningful adaptation (>10 turns stuck, >15 attempts without strategy change)
- The agent fabricated results — produced output with values/conclusions that were never actually computed or verified during the trajectory
- The agent marked complete while the terminal was non-functional

Be strict. When in doubt, discard.

Respond in JSON format ONLY:
```json
{{
  "shortcutting": true/false,
  "shortcut_details": "how the agent obtained answers from the environment rather than computing them, or null if no shortcutting",
  "fabrication": true/false,
  "fabrication_details": "how the agent fabricated results without actually computing them, or null if no fabrication",
  "productive_behavior": true/false,
  "behavior_issues": ["specific unproductive patterns observed, empty if none"],
  "decision": "keep" | "discard",
  "reason": "brief explanation focusing on what behavior this trajectory would teach"
}}
```
"""


# ---------------------------------------------------------------------------
# Suspicious filename detection
# ---------------------------------------------------------------------------
SUSPICIOUS_FILENAME_KEYWORDS = [
    "solution", "fixed", "answer", "expected_output", "expected_answer",
    "correct", "bugfix", "bugsolution", "hint", "cheat", "reference_answer",
    "ground_truth", "answer_key", "solution_key",
]


def _is_suspicious_read(keystrokes: str) -> bool:
    """Check if a command is reading a file with a suspicious name."""
    ks = keystrokes.strip().lower()
    # Must be a read command (cat/head/tail/less without redirect or heredoc)
    if not any(ks.startswith(cmd) for cmd in ["cat ", "head ", "tail ", "less ", "more "]):
        return False
    if ">" in ks or "<<" in ks:
        return False
    # Check for suspicious keywords in the filename
    return any(kw in ks for kw in SUSPICIOUS_FILENAME_KEYWORDS)


# ---------------------------------------------------------------------------
# Trajectory formatting
# ---------------------------------------------------------------------------
def format_trajectory_for_review(traj_data: dict) -> tuple[str, str]:
    """
    Format a trajectory into a readable string for LLM review.
    Returns (trajectory_content, outcome).
    """
    messages = traj_data.get("messages", [])
    data_type = traj_data.get("data_type", "unknown")
    outcome = "SUCCESS (reward=1)" if "success" in data_type else "FAILED (reward=0)"

    lines = []
    turn = 0

    for msg in messages:
        role = msg.get("role", "?")
        content = msg.get("content", "")

        if role == "system":
            # Skip system message for brevity, just note it exists
            lines.append(f"[SYSTEM MESSAGE: {len(content)} chars - task setup]")
            lines.append("")
            continue

        if role == "user":
            turn += 1
            # Truncate very long observations
            if len(content) > 3000:
                content = content[:1500] + "\n... [OBSERVATION TRUNCATED] ...\n" + content[-1000:]
            lines.append(f"--- Turn {turn}: Environment Observation ---")
            lines.append(content)
            lines.append("")

        elif role == "assistant":
            lines.append(f"--- Turn {turn}: Agent Action ---")
            # Try to parse as JSON (terminus format)
            try:
                parsed = json.loads(content)
                # Show thought/analysis
                thought = parsed.get("thought", "") or parsed.get("analysis", "")
                if thought:
                    lines.append(f"[Thought]: {thought}")

                # Show commands
                commands = parsed.get("commands", [])
                if commands:
                    lines.append(f"[Commands]:")
                    for cmd in commands:
                        ks = cmd.get("keystrokes", "")
                        if ks:
                            # Flag suspicious file reads
                            if _is_suspicious_read(ks):
                                lines.append(
                                    f"  [⚠️ WARNING: Agent reads file with suspicious name "
                                    f"— possible pre-existing solution/answer]"
                                )
                            # Truncate very long heredocs
                            if len(ks) > 500:
                                ks = ks[:300] + "\n... [CODE TRUNCATED] ...\n" + ks[-100:]
                            lines.append(f"  $ {ks}")

                # Show task_complete
                if parsed.get("task_complete"):
                    lines.append(f"[TASK MARKED COMPLETE]")
            except json.JSONDecodeError:
                # Raw text response
                if len(content) > 2000:
                    content = content[:1500] + "\n... [TRUNCATED] ..."
                lines.append(content)

            lines.append("")

    trajectory_content = "\n".join(lines)

    # Final truncation if still too long
    if len(trajectory_content) > MAX_TRAJ_SIZE:
        # Keep beginning and end
        half = MAX_TRAJ_SIZE // 2
        trajectory_content = (
            trajectory_content[:half]
            + "\n\n... [MIDDLE OF TRAJECTORY TRUNCATED] ...\n\n"
            + trajectory_content[-half:]
        )

    return trajectory_content, outcome


# ---------------------------------------------------------------------------
# LLM calling
# ---------------------------------------------------------------------------
def call_llm(
    prompt: str,
    system_prompt: str,
    api_base: str,
    api_key: str,
    model: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    retries: int = DEFAULT_RETRIES,
    sleep: float = DEFAULT_SLEEP,
) -> Optional[str]:
    """Call the LLM API via litellm and return the response text."""
    messages = [
        {"role": "system", "content": system_prompt},
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
                temperature=0.2,
                top_p=0.8,
                extra_body={
                    "top_k": 20,
                    "chat_template_kwargs": {"enable_thinking": True},
                },
            )
            content = resp.choices[0].message.content
            # If content is empty but there might be thinking, return None to retry
            if not content or not content.strip():
                if attempt < retries - 1:
                    print(f"  Empty response, retrying...", file=sys.stderr)
                    time.sleep(sleep)
                    continue
                return None
            return content
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

    # Try ```json block
    json_match = re.search(r"```json\s*\n?(.*?)\n?```", response, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try bare JSON
    brace_match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(0))
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Review worker
# ---------------------------------------------------------------------------
def review_trajectory(
    traj_data: dict,
    idx: int,
    api_base: str,
    api_key: str,
    model: str,
    max_tokens: int,
    retries: int,
    sleep: float,
) -> dict:
    """Review a single trajectory."""
    tid = traj_data.get("id", f"unknown_{idx}")

    trajectory_content, outcome = format_trajectory_for_review(traj_data)
    prompt = REVIEW_USER_PROMPT_TEMPLATE.format(
        trajectory_content=trajectory_content,
        outcome=outcome,
    )

    response = call_llm(
        prompt, REVIEW_SYSTEM_PROMPT,
        api_base, api_key, model, max_tokens, retries, sleep,
    )
    parsed = parse_llm_response(response)

    result = {"id": tid, "data_type": traj_data.get("data_type", "unknown")}

    if parsed:
        result["decision"] = parsed.get("decision", "discard")
        result["shortcutting"] = parsed.get("shortcutting", False)
        result["shortcut_details"] = parsed.get("shortcut_details")
        result["fabrication"] = parsed.get("fabrication", False)
        result["fabrication_details"] = parsed.get("fabrication_details")
        result["productive_behavior"] = parsed.get("productive_behavior", True)
        result["behavior_issues"] = parsed.get("behavior_issues", [])
        result["reason"] = parsed.get("reason", "")
    else:
        result["decision"] = "discard"
        result["parse_error"] = True
        result["reason"] = "Failed to parse LLM response"

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Trajectory Quality Review for SFT filtering"
    )
    parser.add_argument(
        "--source", required=True,
        help="Input JSONL file with trajectories",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output JSONL file with kept trajectories (optional)",
    )
    parser.add_argument(
        "--report", default="trajectory_review_report.jsonl",
        help="Report JSONL file with review results for all trajectories",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--api-key", default=DEFAULT_API_KEY)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--sleep", type=float, default=DEFAULT_SLEEP)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--limit", type=int, default=0, help="Limit number of trajectories (0=all)")
    parser.add_argument("--dry-run", action="store_true", help="Print prompt for first trajectory only")
    args = parser.parse_args()

    # Load trajectories
    trajectories = []
    with open(args.source, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            trajectories.append(json.loads(line))

    if args.limit > 0:
        trajectories = trajectories[:args.limit]

    print(f"Loaded {len(trajectories)} trajectories from {args.source}")

    # Dry run
    if args.dry_run:
        traj = trajectories[0]
        content, outcome = format_trajectory_for_review(traj)
        prompt = REVIEW_USER_PROMPT_TEMPLATE.format(
            trajectory_content=content, outcome=outcome,
        )
        print(f"Trajectory ID: {traj.get('id')}")
        print(f"Prompt length: {len(prompt)} chars")
        print(f"{'='*60}")
        print(prompt[:5000])
        print("...")
        return

    # Review
    results = []
    lock = Lock()
    completed = [0]

    def worker(idx_traj):
        idx, traj = idx_traj
        result = review_trajectory(
            traj, idx,
            args.api_base, args.api_key, args.model,
            args.max_tokens, args.retries, args.sleep,
        )
        with lock:
            completed[0] += 1
            decision = result.get("decision", "?")
            flags = []
            if result.get("shortcutting"):
                flags.append("SHORTCUT")
            if result.get("fabrication"):
                flags.append("FABRICATION")
            if not result.get("productive_behavior", True):
                flags.append("UNPRODUCTIVE")
            flag_str = ",".join(flags) if flags else "OK"
            print(
                f"  [{completed[0]}/{len(trajectories)}] {result['id']}: "
                f"{decision} | {flag_str} | "
                f"{result.get('reason', '')[:60]}"
            )
        return idx, result

    print(f"\nReviewing with model={args.model}, workers={args.workers}...")
    print("-" * 60)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(worker, (i, t)): i for i, t in enumerate(trajectories)}
        for future in as_completed(futures):
            try:
                idx, result = future.result()
                results.append((idx, result))
            except Exception as e:
                idx = futures[future]
                print(f"  ERROR idx={idx}: {e}", file=sys.stderr)
                results.append((idx, {
                    "id": trajectories[idx].get("id", f"unknown_{idx}"),
                    "decision": "discard",
                    "reason": f"Processing error: {e}",
                    "shortcutting": False,
                    "productive_behavior": False,
                }))

    # Sort by original index
    results.sort(key=lambda x: x[0])

    # Summary
    total = len(results)
    kept = sum(1 for _, r in results if r.get("decision") == "keep")
    discarded = sum(1 for _, r in results if r.get("decision") == "discard")
    shortcutted = sum(1 for _, r in results if r.get("shortcutting"))
    fabricated = sum(1 for _, r in results if r.get("fabrication"))
    unproductive = sum(1 for _, r in results if not r.get("productive_behavior", True))

    print(f"\n{'='*60}")
    print("TRAJECTORY REVIEW SUMMARY")
    print("="*60)
    print(f"  Total:        {total}")
    print(f"  Keep:         {kept} ({kept/total*100:.1f}%)")
    print(f"  Discard:      {discarded} ({discarded/total*100:.1f}%)")
    print(f"  Shortcutting: {shortcutted}")
    print(f"  Fabrication:  {fabricated}")
    print(f"  Unproductive: {unproductive}")
    print("="*60)

    # Write report
    with open(args.report, "w", encoding="utf-8") as f:
        for _, r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Report saved to {args.report}")

    # Write filtered output
    if args.output:
        keep_ids = {r["id"] for _, r in results if r.get("decision") == "keep"}
        kept_count = 0
        with open(args.output, "w", encoding="utf-8") as f:
            for traj in trajectories:
                if traj.get("id") in keep_ids:
                    f.write(json.dumps(traj, ensure_ascii=False) + "\n")
                    kept_count += 1
        print(f"Filtered output: {kept_count} trajectories saved to {args.output}")


if __name__ == "__main__":
    main()
