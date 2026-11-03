#!/usr/bin/env python3
"""Assemble Phase 2 instruction from phase1_output.md and prompt skeleton template.

This script runs inside the container between Phase 1 and Phase 2:
1. Reads /app/phase1_output.md (output of Phase 1 — category + scenario templates)
2. Reads /app/templates/prompt_skeleton.md (fixed skeleton template)
3. Reads /app/templates/difficulty/{level}.md (difficulty requirements)
4. Combines them into /app/phase2_instruction.md (input for Phase 2)

Phase 1 outputs free-form markdown with two sections:
  === CATEGORY ===
  (category template content, like our hand-written category templates)

  === SCENARIO ===
  (scenario template content, like our hand-written scenario templates)

These sections are inserted into the same variable slots ($category_content,
$scenario_content) that the single-phase prompt uses, making the Phase 2 prompt
structurally identical to the single-phase prompt plus a search tool section.

Usage:
    python3 /app/tools/assemble_prompt.py
"""

import re
import sys
from pathlib import Path
from string import Template


PHASE1_OUTPUT_PATH = Path("/app/phase1_output.md")
SKELETON_PATH = Path("/app/templates/prompt_skeleton.md")
DIFFICULTY_DIR = Path("/app/templates/difficulty")
EXAMPLES_DIR = Path("/app/examples")
OUTPUT_PATH = Path("/app/phase2_instruction.md")

# Difficulty level is passed via a marker file in the templates directory
# (written by generate_meta_task.py, COPYed into container via COPY templates/).
# Fallback to task.toml, then "hard" if not found.
DIFFICULTY_MARKER = Path("/app/templates/.difficulty")


def load_phase1_output() -> tuple[str, str, str]:
    """Load and parse phase1_output.md into category_content, scenario_content, and category_display.

    Returns:
        (category_content, scenario_content, category_display)
    """
    if not PHASE1_OUTPUT_PATH.exists():
        print(f"[ERROR] Phase 1 output not found: {PHASE1_OUTPUT_PATH}")
        print("[ERROR] Phase 1 may have failed to produce phase1_output.md")
        sys.exit(1)

    text = PHASE1_OUTPUT_PATH.read_text()

    # Split by section markers
    category_marker = "=== CATEGORY ==="
    scenario_marker = "=== SCENARIO ==="

    if category_marker not in text:
        print(f"[ERROR] Missing '{category_marker}' marker in phase1_output.md")
        sys.exit(1)
    if scenario_marker not in text:
        print(f"[ERROR] Missing '{scenario_marker}' marker in phase1_output.md")
        sys.exit(1)

    # Extract sections: everything between CATEGORY marker and SCENARIO marker is category,
    # everything after SCENARIO marker is scenario
    cat_start = text.index(category_marker) + len(category_marker)
    scen_start = text.index(scenario_marker)

    category_content = text[cat_start:scen_start].strip()
    scenario_content = text[scen_start + len(scenario_marker):].strip()

    # Extract category display name from "### Category: ..." header
    category_display = "General"
    match = re.search(r"^###\s+Category:\s*(.+)$", category_content, re.MULTILINE)
    if match:
        category_display = match.group(1).strip()

    return category_content, scenario_content, category_display


def get_difficulty_level() -> str:
    """Determine difficulty level from marker file or task.toml."""
    # Try marker file first (written by generate_meta_task.py)
    if DIFFICULTY_MARKER.exists():
        return DIFFICULTY_MARKER.read_text().strip().lower()

    # Try task.toml
    task_toml = Path("/app/task.toml")
    if task_toml.exists():
        import tomllib
        data = tomllib.loads(task_toml.read_text())
        return data.get("metadata", {}).get("difficulty", "hard")

    return "hard"


def load_difficulty_section(level: str) -> str:
    """Load the base difficulty requirements template."""
    path = DIFFICULTY_DIR / f"{level}.md"
    if path.exists():
        return path.read_text()
    return f"**{level.upper()} difficulty requirements.**"


def build_example_list() -> str:
    """Build the example list from available examples."""
    if not EXAMPLES_DIR.exists():
        return ""
    examples = [
        d.name for d in sorted(EXAMPLES_DIR.iterdir())
        if d.is_dir() and not d.name.startswith("_")
    ]
    lines = []
    for ex in examples:
        lines.append(f"- `/app/examples/{ex}/` — a real completed task")
    return "\n".join(lines)


SEARCH_TOOL_PATH = Path("/app/tools/search_materials.py")

TOOLS_SECTION = """
---

## Material Search Tool

A search tool is available to find real-world materials (code, data) for your task. Use it to ground your task in authentic resources.

**Tool:** `/app/tools/search_materials.py`

```bash
python3 /app/tools/search_materials.py search-github "<query>"     # Search GitHub repos
python3 /app/tools/search_materials.py search-hf "<query>"         # Search HuggingFace datasets
python3 /app/tools/search_materials.py clone <owner/repo>          # Clone a GitHub repo
python3 /app/tools/search_materials.py download-hf <dataset_id>    # Download HF dataset files
python3 /app/tools/search_materials.py list                        # List downloaded materials
python3 /app/tools/search_materials.py cleanup [name]              # Clean up materials
```

Options: `--limit N`, `--max-size MB`, `--max-files N`, `--max-file-size MB`, `--file PATTERN`

**How to use what you find:**
- **As real data (strongly preferred)** — download real data files (CSV, JSON, configs, logs, databases) and COPY them directly into your task environment. Real data makes tasks more authentic and challenging. Do NOT generate synthetic data when real data is available.
- **As a real codebase environment (strongly preferred)** — clone an entire repo and use it as-is for the task environment. The messiness and complexity of real projects naturally increases task difficulty — the agent must navigate unfamiliar code, understand undocumented structures, and work within real constraints.
- **As a starting point** — clone a project, extract relevant parts, adapt or transform them for your task design.
- **As inspiration (last resort)** — only if you cannot find usable materials after multiple search attempts.

**Your Dockerfile MUST include at least one `COPY` from `/app/materials/` into the task container.** If the first repo you find has empty files (Git LFS pointers) or is unsuitable, search for alternatives — do not fall back to generating everything synthetically.

**Search iteratively** — if one query doesn't yield useful results, try different keywords, broaden/narrow the scope, or explore related topics. Search multiple times until you find materials that fit your task design well. Downloaded materials go to `/app/materials/` (200 MB limit).

"""


def main():
    print("[ASSEMBLE] Loading phase1_output.md...")
    category_content, scenario_content, category_display = load_phase1_output()
    print(f"[ASSEMBLE] Extracted category: {category_display}")

    print("[ASSEMBLE] Loading skeleton template...")
    if not SKELETON_PATH.exists():
        print(f"[ERROR] Skeleton template not found: {SKELETON_PATH}")
        sys.exit(1)
    skeleton = SKELETON_PATH.read_text()

    difficulty = get_difficulty_level()
    print(f"[ASSEMBLE] Difficulty: {difficulty}")

    # Build tools section and workflow — conditional on search tool availability
    has_search_tool = SEARCH_TOOL_PATH.exists()
    tools_section = ""
    if has_search_tool:
        tools_section = TOOLS_SECTION
        print("[ASSEMBLE] Search tool found, including tools section")
        workflow_steps = (
            "1. **Search** — Use the search tool to find real-world materials related to your task category. Try multiple queries.\n"
            "2. **Explore** — Study the reference example, task template, and downloaded materials.\n"
            "3. **Design** — Decide which task construction approach to use (see above). Plan how instruction, environment, solution, and tests fit together.\n"
            "4. **Implement** — Copy `/app/examples/_task_template/` to `/app/output/` and fill in each component.\n"
            "5. **Validate** — Run solve.sh, then run tests, then check cross-component consistency (see Self-Validation below). Fix any issues and repeat.\n"
            "6. **Clean up** — Remove validation artifacts."
        )
    else:
        print("[ASSEMBLE] No search tool found, skipping tools section")
        workflow_steps = (
            "1. **Explore** — Study the reference example and task template in `/app/examples/`.\n"
            "2. **Design** — Decide which task construction approach to use (see above). Plan how instruction, environment, solution, and tests fit together.\n"
            "3. **Implement** — Copy `/app/examples/_task_template/` to `/app/output/` and fill in each component.\n"
            "4. **Validate** — Run solve.sh, then run tests, then check cross-component consistency (see Self-Validation below). Fix any issues and repeat.\n"
            "5. **Clean up** — Remove validation artifacts."
        )

    # Build all template variables — same as single-phase prompt uses
    variables = {
        "category_display": category_display,
        "example_list": build_example_list(),
        "tools_section": tools_section,
        "workflow_steps": workflow_steps,
        "category_content": category_content,
        "scenario_content": scenario_content,
        "difficulty_section": load_difficulty_section(difficulty),
        "DIFFICULTY": difficulty.upper(),
        "difficulty": difficulty,
    }

    # Render template
    result = Template(skeleton).safe_substitute(variables)

    # Write output
    OUTPUT_PATH.write_text(result)
    print(f"[ASSEMBLE] Wrote phase2 instruction to {OUTPUT_PATH}")
    print(f"[ASSEMBLE] Category: {category_display}, Difficulty: {difficulty}")
    print(f"[ASSEMBLE] Category content length: {len(category_content)} chars")
    print(f"[ASSEMBLE] Scenario content length: {len(scenario_content)} chars")


if __name__ == "__main__":
    main()
