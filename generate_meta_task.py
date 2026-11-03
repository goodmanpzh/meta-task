#!/usr/bin/env python3
"""
Meta-Task Generator

This script generates meta-tasks by combining different templates, categories,
examples, and configurations. Each generated meta-task is a terminal-based task
that instructs an AI agent to generate another terminal-based task.

Usage:
    # Fully random generation
    python generate_meta_task.py --output /path/to/output

    # Specify category and scenario
    python generate_meta_task.py --output /path/to/output \
        --category git_operations --scenario narrative

    # Batch generation
    python generate_meta_task.py --output /path/to/batch --count 10
    python generate_meta_task.py --output ./output/batch_hard_v1 --count 10 --difficulty hard

    # List available options
    python generate_meta_task.py --list
"""

import argparse
import json
import random
import shutil
import string
import sys
from pathlib import Path
from datetime import datetime


class MetaTaskGenerator:
    """Generator for creating meta-tasks with combinatorial diversity."""

    # How many real examples to include per meta-task (plus 1 case template)
    DEFAULT_NUM_EXAMPLES = 1

    # Selection weights for scenario templates.
    # All weights are equal by default => uniform random selection.
    # Adjust individual values to bias generation toward specific scenarios.
    # Any scenario not listed here falls back to the default weight in _weighted_choice.
    SCENARIO_WEIGHTS = {
        "minimal": 1.0,
        "creative": 1.0,
        "casual_user": 1.0,
        "structured_request": 1.0,
        "terminal_dump": 1.0,
        "emergency": 1.0,
        "specification": 1.0,
        "narrative": 1.0,
        "followup": 1.0,
        "multi_request": 1.0,
    }

    # Selection weights for category templates.
    # All weights are equal by default => uniform random selection.
    # Adjust individual values to bias generation toward specific categories.
    # Any category not listed here falls back to the default weight in _weighted_choice.
    CATEGORY_WEIGHTS = {
        # Core terminal skills
        "debugging": 1.0,
        "shell_scripting": 1.0,
        "system_admin": 1.0,
        "environment_dependencies": 1.0,
        "data_processing": 1.0,
        "file_operations": 1.0,
        "text_processing": 1.0,
        "git_operations": 1.0,
        # Exploration & reasoning
        "puzzle_investigation": 1.0,
        "system_orchestration": 1.0,
        "incident_response": 1.0,
        # Security
        "security_ctf": 1.0,
        "code_audit": 1.0,
        "cryptanalysis": 1.0,
        # Software engineering
        "software_engineering": 1.0,
        "algorithm": 1.0,
        "compilation_build": 1.0,
        "optimization": 1.0,
        "code_migration": 1.0,
        "testing_qa": 1.0,
        # Infrastructure
        "networking": 1.0,
        "database": 1.0,
        "web_development": 1.0,
        "distributed_systems": 1.0,
        "message_queue": 1.0,
        "devops_cicd": 1.0,
        "monitoring_observability": 1.0,
        "api_design": 1.0,
        # ML & scientific
        "ml_training": 1.0,
        "scientific_computing": 1.0,
        "physics_computing": 1.0,
        "bioinformatics": 1.0,
        "distributed_ml": 1.0,
        # Domain-specific & niche
        "financial_engineering": 1.0,
        "games": 1.0,
        "fpga_hardware": 1.0,
        "functional_languages": 1.0,
        "video_multimedia": 1.0,
        "code_golf": 1.0,
    }

    def __init__(self, base_dir: Path, examples_dir: Path = None):
        self.base_dir = Path(base_dir)
        self.templates_dir = self.base_dir / "templates"
        self.examples_dir = Path(examples_dir) if examples_dir else self.base_dir / "examples"
        self.base_files_dir = self.base_dir / "base"
        self._all_examples = self._scan_examples()
        self._all_topics = self._load_topics()
        self._all_scenario_dims = self._load_scenario_dimensions()
        self._phase1_mode = None  # Set during multiphase instruction building
        self._phase1_topic = None  # Set during multiphase instruction building
        self._phase1_scenario_dim = None  # Set during multiphase instruction building

    def _scan_examples(self) -> list[str]:
        """Scan examples/ directory for all available example task folders."""
        if not self.examples_dir.exists():
            return []
        return [
            d.name for d in sorted(self.examples_dir.iterdir())
            if d.is_dir() and not d.name.startswith("_")
        ]

    def _load_topics(self) -> list[str]:
        """Load topic list from templates/topics.txt."""
        topics_path = self.templates_dir / "topics.txt"
        if not topics_path.exists():
            return []
        topics = []
        for line in topics_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                topics.append(line)
        return topics

    def _load_scenario_dimensions(self) -> list[str]:
        """Load scenario dimension constraints from templates/scenario_dimensions.txt."""
        dims_path = self.templates_dir / "scenario_dimensions.txt"
        if not dims_path.exists():
            return []
        dims = []
        for line in dims_path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                dims.append(line)
        return dims

    def _copy_search_tool(self, env_dir: Path) -> bool:
        """Copy the search_materials.py tool into the environment's tools/ dir."""
        tool_src = self.base_files_dir / "search_materials.py"
        if tool_src.exists():
            tools_dir = env_dir / "tools"
            tools_dir.mkdir(exist_ok=True)
            shutil.copy(tool_src, tools_dir / "search_materials.py")
            return True
        return False

    def _get_category_display_name(self, category: str) -> str:
        """Parse category display name from the first line of the category template file."""
        category_path = self.templates_dir / "categories" / f"{category}.md"
        if category_path.exists():
            first_line = category_path.read_text().split("\n", 1)[0]
            prefix = "### Category: "
            if first_line.startswith(prefix):
                return first_line[len(prefix):].strip()
        return category.replace("_", " ").title()

    @staticmethod
    def _shuffle_markdown_bullets(text: str) -> str:
        """Shuffle bullet-point lists in markdown text to reduce ordering bias.

        Handles two formats:
        1. Simple bullet lists: consecutive lines starting with '- '
        2. Sub-grouped lists: '*Header:*' followed by '- ' items

        Preserves all non-bullet content (headers, paragraphs, etc.) in place.
        """
        lines = text.split("\n")
        result = []
        i = 0

        while i < len(lines):
            line = lines[i]

            # Check if this is a sub-group header like '*Code Bugs:*'
            stripped = line.strip()
            if stripped.startswith("*") and stripped.endswith("*") and ":" in stripped:
                # Collect all sub-groups with their bullets
                groups = []
                while i < len(lines):
                    sl = lines[i].strip()
                    if sl.startswith("*") and sl.endswith("*") and ":" in sl:
                        # New sub-group header
                        group_header = lines[i]
                        group_bullets = []
                        i += 1
                        while i < len(lines) and lines[i].startswith("- "):
                            group_bullets.append(lines[i])
                            i += 1
                        random.shuffle(group_bullets)
                        groups.append((group_header, group_bullets))
                    elif sl.startswith("- "):
                        # Bullet without sub-group (shouldn't happen mid-group, but handle)
                        groups[-1][1].append(lines[i])
                        i += 1
                    elif sl == "":
                        # Blank line between sub-groups
                        i += 1
                    else:
                        break

                # Shuffle the sub-groups themselves
                random.shuffle(groups)
                for group_header, group_bullets in groups:
                    result.append("")
                    result.append(group_header)
                    result.extend(group_bullets)
                result.append("")
                continue

            # Check if this starts a simple bullet block
            if line.startswith("- "):
                bullets = []
                while i < len(lines) and lines[i].startswith("- "):
                    bullets.append(lines[i])
                    i += 1
                random.shuffle(bullets)
                result.extend(bullets)
                continue

            result.append(line)
            i += 1

        return "\n".join(result)

    def list_scenarios(self) -> list[str]:
        """List available scenario templates."""
        scenarios_dir = self.templates_dir / "scenarios"
        if not scenarios_dir.exists():
            return []
        return [f.stem for f in scenarios_dir.glob("*.md")]

    def _weighted_choice(self, items: list[str], weights: dict[str, float]) -> str:
        """Select an item using weighted probabilities."""
        # Get weights for available items, default to equal weight for unknown items
        available_weights = []
        for item in items:
            available_weights.append(weights.get(item, 1.0))

        # Normalize weights
        total = sum(available_weights)
        normalized = [w / total for w in available_weights]

        # Weighted random choice
        r = random.random()
        cumulative = 0
        for item, weight in zip(items, normalized):
            cumulative += weight
            if r <= cumulative:
                return item
        return items[-1]  # Fallback

    def list_categories(self) -> list[str]:
        """List available category templates."""
        categories_dir = self.templates_dir / "categories"
        if not categories_dir.exists():
            return []
        return [f.stem for f in categories_dir.glob("*.md")]

    def list_examples(self) -> list[str]:
        """List all available example tasks."""
        return list(self._all_examples)

    def generate(
        self,
        output_dir: Path,
        scenario: str = None,
        category: str = None,
        examples: list[str] = None,
        difficulty: str = None,
        seed: int = None,
        enable_search_tool: bool = False,
        multiphase: bool = False,
        topic: str = None
    ) -> Path:
        """
        Generate a meta-task by combining templates and examples.

        Args:
            output_dir: Directory to write the meta-task to
            scenario: Scenario template name (e.g., "minimal", "narrative")
            category: Category template name (e.g., "git_operations", "security_ctf")
            examples: List of example task paths to include
            difficulty: Task difficulty ("easy", "medium", "hard")
            seed: Random seed for reproducibility
            enable_search_tool: Whether to include the search_materials.py tool
            multiphase: Whether to generate a multi-phase meta-task
            topic: Specific topic for multiphase mode (overrides random selection)

        Returns:
            Path to the generated meta-task directory
        """
        if seed is not None:
            random.seed(seed)

        # Select or randomize options
        available_scenarios = self.list_scenarios()
        available_categories = self.list_categories()

        if not available_scenarios:
            raise ValueError("No scenario templates found")
        if not available_categories:
            raise ValueError("No category templates found")

        # Weighted random selection for scenarios (uniform by default; see SCENARIO_WEIGHTS)
        if scenario is None:
            scenario = self._weighted_choice(available_scenarios, self.SCENARIO_WEIGHTS)
        # Weighted random selection for categories (uniform by default; see CATEGORY_WEIGHTS)
        if category is None:
            category = self._weighted_choice(available_categories, self.CATEGORY_WEIGHTS)
        difficulty = difficulty or random.choice(["medium", "hard"])

        # Select random example(s) from the pool (category-independent)
        if examples is None:
            if self._all_examples:
                num_to_select = min(self.DEFAULT_NUM_EXAMPLES, len(self._all_examples))
                examples = random.sample(self._all_examples, num_to_select)
            else:
                examples = []

        # Create output directory
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Search tool is now optional for multiphase mode (controlled by --enable-search-tool)

        # 2. Create environment directory and copy examples
        env_dir = output_dir / "environment"
        env_dir.mkdir(exist_ok=True)

        # 2a. Copy search tool if enabled
        has_search_tool = False
        if enable_search_tool:
            has_search_tool = self._copy_search_tool(env_dir)

        # 2b. For multiphase: copy assemble script, skeleton template, and difficulty templates
        if multiphase:
            self._copy_multiphase_assets(env_dir, difficulty)

        # 1. Generate instruction.md
        if multiphase:
            instruction = self._build_phase1_instruction(scenario, category, difficulty, topic=topic)
        else:
            instruction = self._build_instruction(scenario, category, difficulty, examples, has_search_tool)
        (output_dir / "instruction.md").write_text(instruction)

        examples_out = env_dir / "examples"
        examples_out.mkdir(exist_ok=True)

        # Copy task template skeleton
        template_src = self.templates_dir / "case_template"
        if template_src.exists():
            template_dst = examples_out / "_task_template"
            if template_dst.exists():
                shutil.rmtree(template_dst)
            shutil.copytree(template_src, template_dst)

        for example in examples:
            src = self.examples_dir / example
            if src.exists():
                dst = examples_out / Path(example).name
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)

        # 3. Generate task.toml
        self._generate_task_toml(output_dir, category, difficulty)

        # 4. Generate Dockerfile
        self._generate_dockerfile(output_dir, examples, has_search_tool, multiphase)

        # 5. Generate tests directory
        self._generate_tests(output_dir)

        # 6. Generate solution directory (empty solve.sh placeholder)
        self._generate_solution(output_dir)

        # 7. Write generation metadata
        self._write_metadata(output_dir, scenario, category, difficulty, examples, seed, multiphase)

        return output_dir

    def _get_difficulty_requirements(self, difficulty: str) -> str:
        """Get difficulty-specific requirements text."""
        template_path = self.templates_dir / "difficulty" / f"{difficulty}.md"
        if template_path.exists():
            return template_path.read_text()
        # Fallback for unknown difficulty levels
        return f"**{difficulty.upper()} difficulty requirements.**"

    def _build_instruction(
        self,
        scenario: str,
        category: str,
        difficulty: str,
        examples: list[str],
        has_search_tool: bool = False
    ) -> str:
        """Build the instruction.md content by combining section templates."""

        # Read scenario template
        scenario_path = self.templates_dir / "scenarios" / f"{scenario}.md"
        scenario_content = scenario_path.read_text() if scenario_path.exists() else ""

        # Read category template and shuffle bullet lists to reduce ordering bias
        category_path = self.templates_dir / "categories" / f"{category}.md"
        category_content = category_path.read_text() if category_path.exists() else ""
        category_content = self._shuffle_markdown_bullets(category_content)

        # Build example list (real examples only)
        example_list = "\n".join([f"- `/app/examples/{Path(e).name}/` — a real completed task" for e in examples])

        # Category display name from template first line
        category_display = self._get_category_display_name(category)

        # Tools section (search tool documentation)
        tools_section = ""
        if has_search_tool:
            tools_section = """
### Material Search Tool — Build Tasks from Real Materials

We want the tasks you generate to feel **real** — grounded in actual open-source code and data, not synthetic toy problems. A search tool is available for you to find, download, and **incorporate** real-world materials into your task.

The core idea: **search for relevant resources → download them → understand their content → modify/adapt them to create your task challenge**. The downloaded materials should end up **physically present** in your task's Docker container (via COPY in the Dockerfile), so the solving agent works with real code or real data.

**Tool:** `/app/tools/search_materials.py`

```bash
python /app/tools/search_materials.py search-github "<query>"     # Search GitHub repos
python /app/tools/search_materials.py search-hf "<query>"         # Search HuggingFace datasets
python /app/tools/search_materials.py clone <owner/repo>          # Clone a GitHub repo
python /app/tools/search_materials.py download-hf <dataset_id>    # Download HF dataset files
python /app/tools/search_materials.py list                        # List downloaded materials
python /app/tools/search_materials.py cleanup [name]              # Clean up materials
```

Options: `--limit N` (result count), `--max-size MB` (repo size cap), `--max-files N` / `--max-file-size MB` (HF limits), `--file PATTERN` (HF filename filter)

**How to search effectively:**

Use keywords related to your task category, the tools/technologies involved, or the kind of resource you want for your task design. GitHub is good for code and projects; HuggingFace is good for data files (CSV, JSON, Parquet, etc.). Overly specific queries may return nothing — keep keywords short and general. If one query doesn't yield useful results, try different terms or related concepts.

Search results show each repo's description and stars (GitHub) or download count (HuggingFace), which helps you quickly judge relevance. Don't just look at the top results by stars — smaller repos can be more interesting and diverse as task materials. Also pay attention to README files in cloned repos — they sometimes reference other useful resources.

**How to use what you find:**

Once you find something promising, clone or download it, then read through the files to understand the content. Based on what you find, design your task around it — for example, you might create challenges based on real data, ask the agent to build on top of a real project, design tasks around extending or adapting real code, or use real configurations as the foundation for deployment tasks. The key is that the real materials become the foundation of your task, not just inspiration.

You can also search based on your own task ideas — if you have a concept in mind, search for resources that would make it more realistic, then adapt what you find.

After incorporating materials, use `COPY` in your Dockerfile to place the relevant files from `/app/materials/` into the task container. You don't need to use everything you downloaded — pick the parts that serve your task best. **Your Dockerfile MUST include at least one `COPY` from `/app/materials/`.**

**Important:** Do NOT just search, read the results, and then synthesize everything from scratch. The whole point is to have real files in the container. If the first repo has empty files (Git LFS pointers) or is unsuitable, search for alternatives — do not fall back to generating everything synthetically. Downloaded materials go to `/app/materials/` (200 MB total limit).

"""

        # Build difficulty-specific requirements
        difficulty_section = self._get_difficulty_requirements(difficulty)

        # Load prompt template
        prompt_path = self.templates_dir / "prompt.md"
        raw = prompt_path.read_text() + "\n"

        # Substitute template variables
        variables = {
            "category_display": category_display,
            "example_list": example_list,
            "tools_section": tools_section,
            "category_content": category_content,
            "scenario_content": scenario_content,
            "DIFFICULTY": difficulty.upper(),
            "difficulty": difficulty,
            "difficulty_section": difficulty_section,
        }

        instruction = string.Template(raw).safe_substitute(variables)
        return instruction

    def _build_phase1_instruction(self, scenario: str, category: str, difficulty: str, topic: str = None) -> str:
        """Build the Phase 1 instruction for multiphase mode.

        Selects a random topic from topics.txt to anchor the category generation.
        Provides a category template (as format reference) and scenario template.
        """
        self._phase1_mode = "seeded"  # Always seeded now

        # Use specified topic or select a random one
        if topic:
            pass  # Use as-is
        elif self._all_topics:
            topic = random.choice(self._all_topics)
        else:
            topic = category.replace("_", " ")
        self._phase1_topic = topic

        # Select a random scenario dimension constraint
        if self._all_scenario_dims:
            scenario_dim = random.choice(self._all_scenario_dims)
        else:
            scenario_dim = "Natural and varied — you decide the detail level and style."
        self._phase1_scenario_dim = scenario_dim

        # Read phase1 template
        phase1_path = self.templates_dir / "phase1_instruction.md"
        raw = phase1_path.read_text()

        # Read category template and shuffle (as format reference)
        category_path = self.templates_dir / "categories" / f"{category}.md"
        category_content = category_path.read_text() if category_path.exists() else ""
        category_content = self._shuffle_markdown_bullets(category_content)

        # Read scenario template
        scenario_path = self.templates_dir / "scenarios" / f"{scenario}.md"
        scenario_content = scenario_path.read_text() if scenario_path.exists() else ""

        # Load difficulty requirements for Phase 1
        difficulty_requirements = self._get_difficulty_requirements(difficulty)

        variables = {
            "topic": topic,
            "difficulty": difficulty,
            "difficulty_requirements": difficulty_requirements,
            "scenario_constraint": scenario_dim,
            "category_ref": category_content,
            "scenario_ref": scenario_content,
        }

        return string.Template(raw).safe_substitute(variables)

    def _copy_multiphase_assets(self, env_dir: Path, difficulty: str):
        """Copy additional assets needed for multiphase mode into the environment."""
        # Copy assemble_prompt.py to tools/
        assemble_src = self.base_files_dir / "assemble_prompt.py"
        if assemble_src.exists():
            tools_dir = env_dir / "tools"
            tools_dir.mkdir(exist_ok=True)
            shutil.copy(assemble_src, tools_dir / "assemble_prompt.py")

        # Copy prompt_skeleton.md to templates/
        skeleton_src = self.templates_dir / "prompt_skeleton.md"
        if skeleton_src.exists():
            templates_out = env_dir / "templates"
            templates_out.mkdir(exist_ok=True)
            shutil.copy(skeleton_src, templates_out / "prompt_skeleton.md")

        # Copy difficulty templates
        difficulty_src = self.templates_dir / "difficulty"
        if difficulty_src.exists():
            difficulty_out = env_dir / "templates" / "difficulty"
            if difficulty_out.exists():
                shutil.rmtree(difficulty_out)
            shutil.copytree(difficulty_src, difficulty_out)

        # Write difficulty marker file into templates/ so it gets COPYed to /app/templates/
        templates_out = env_dir / "templates"
        templates_out.mkdir(exist_ok=True)
        (templates_out / ".difficulty").write_text(difficulty)

    def _generate_task_toml(self, output_dir: Path, category: str, difficulty: str):
        """Generate task.toml from template."""
        template_path = self.base_files_dir / "task.toml.template"
        if template_path.exists():
            content = template_path.read_text()
            content = content.replace("{difficulty}", difficulty)
            content = content.replace("{category}", category)
        else:
            content = f"""version = "1.0"

[metadata]
author_name = "Meta-Task Generator"
author_email = "metatask@example.com"
difficulty = "{difficulty}"
category = "meta-task-{category}"
tags = ["task-generation", "meta", "{category}"]
expert_time_estimate_min = 30.0
junior_time_estimate_min = 90.0

[verifier]
type = "script"
script = "tests/test.sh"
timeout_sec = 1800

[agent]
timeout_sec = 3600
setup_timeout_sec = 600

[environment]
type = "docker"
dockerfile = "environment/Dockerfile"
"""
        (output_dir / "task.toml").write_text(content)

    def _generate_dockerfile(self, output_dir: Path, examples: list[str],
                             has_search_tool: bool = False,
                             multiphase: bool = False):
        """Generate Dockerfile from template, optionally adding search tool and templates COPY."""
        template_path = self.base_files_dir / "Dockerfile.template"
        if template_path.exists():
            dockerfile_content = template_path.read_text()
        else:
            dockerfile_content = """FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y procps curl git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir toml pytest
COPY examples/ /app/examples/
# TOOL_COPY_PLACEHOLDER
RUN mkdir -p /app/output
"""
        # Inject tools COPY via placeholder
        # tools/ is needed when: search tool is enabled, OR multiphase (assemble_prompt.py lives there)
        if has_search_tool or multiphase:
            tool_line = "# Copy tools\nCOPY tools/ /app/tools/"
            dockerfile_content = dockerfile_content.replace(
                "# TOOL_COPY_PLACEHOLDER", tool_line
            )
        else:
            dockerfile_content = dockerfile_content.replace(
                "# TOOL_COPY_PLACEHOLDER\n", ""
            )

        # Inject templates COPY for multiphase mode
        if multiphase:
            templates_line = "# Copy templates for prompt assembly\nCOPY templates/ /app/templates/"
            dockerfile_content = dockerfile_content.replace(
                "# TEMPLATES_COPY_PLACEHOLDER", templates_line
            )
        else:
            dockerfile_content = dockerfile_content.replace(
                "# TEMPLATES_COPY_PLACEHOLDER\n", ""
            )

        env_dir = output_dir / "environment"
        env_dir.mkdir(exist_ok=True)
        (env_dir / "Dockerfile").write_text(dockerfile_content)

    def _generate_tests(self, output_dir: Path):
        """Generate tests directory with test.sh and test_outputs.py."""
        tests_dir = output_dir / "tests"
        tests_dir.mkdir(exist_ok=True)

        # Copy test.sh template
        test_sh_template = self.base_files_dir / "tests" / "test.sh.template"
        if test_sh_template.exists():
            shutil.copy(test_sh_template, tests_dir / "test.sh")
        else:
            (tests_dir / "test.sh").write_text("""#!/bin/bash
apt-get update && apt-get install -y curl
curl -LsSf https://astral.sh/uv/0.9.5/install.sh | sh
source $HOME/.local/bin/env
mkdir -p /logs/verifier
cd /app
uv run --with pytest --with toml pytest tests/test_outputs.py -v --tb=short
if [ $? -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi
""")

        # Copy test_outputs.py template
        test_state_template = self.base_files_dir / "tests" / "test_outputs.py.template"
        if test_state_template.exists():
            shutil.copy(test_state_template, tests_dir / "test_outputs.py")
        else:
            (tests_dir / "test_outputs.py").write_text("""from pathlib import Path

OUTPUT_DIR = Path("/app/output")

def test_required_files_exist():
    \"\"\"Check all required files are generated.\"\"\"
    required_files = [
        "instruction.md",
        "task.toml",
        "environment/Dockerfile",
        "solution/solve.sh",
        "tests/test.sh",
        "tests/test_outputs.py",
    ]
    for f in required_files:
        assert (OUTPUT_DIR / f).exists(), f"Missing required file: {f}"
""")

    def _generate_solution(self, output_dir: Path):
        """Generate solution directory with placeholder solve.sh."""
        solution_dir = output_dir / "solution"
        solution_dir.mkdir(exist_ok=True)

        # Create a placeholder that tells the agent what to do
        solve_sh_content = """#!/bin/bash
# This is a placeholder solve.sh for the meta-task.
# The actual solution should be generated by the agent.
#
# As an oracle solution, this script generates a sample task.
# In production, this would be replaced by agent-generated content.

echo "Meta-task: Agent should generate a complete TB task in /app/output/"
echo "This placeholder does not generate a task."
echo "Run with an actual agent to generate tasks."
"""
        (solution_dir / "solve.sh").write_text(solve_sh_content)

    def _write_metadata(
        self,
        output_dir: Path,
        scenario: str,
        category: str,
        difficulty: str,
        examples: list[str],
        seed: int,
        multiphase: bool = False
    ):
        """Write generation metadata for reproducibility."""
        metadata = {
            "generated_at": datetime.now().isoformat(),
            "generator_version": "2.0.0",
            "mode": "multiphase" if multiphase else "single",
            "phase1_input_mode": self._phase1_mode if multiphase else None,
            "phase1_topic": self._phase1_topic if multiphase else None,
            "phase1_scenario_constraint": self._phase1_scenario_dim if multiphase else None,
            "scenario": scenario,
            "category": category,
            "difficulty": difficulty,
            "examples": examples,
            "seed": seed
        }
        (output_dir / "generation_metadata.json").write_text(
            json.dumps(metadata, indent=2)
        )


def main():
    parser = argparse.ArgumentParser(
        description="Generate meta-tasks for terminal-based AI agent task generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output directory for the generated meta-task"
    )
    parser.add_argument(
        "--scenario", "-s",
        help="Scenario template (e.g., minimal, narrative, specification)"
    )
    parser.add_argument(
        "--category", "-c",
        help="Category template (e.g., git_operations, security_ctf)"
    )
    parser.add_argument(
        "--difficulty", "-d",
        choices=["easy", "medium", "hard", "extreme"],
        help="Task difficulty level"
    )
    parser.add_argument(
        "--examples", "-e",
        nargs="+",
        help="Example task paths to include"
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--count", "-n",
        type=int,
        default=1,
        help="Number of meta-tasks to generate (for batch mode)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available scenarios and categories"
    )
    parser.add_argument(
        "--base-dir", "-b",
        type=Path,
        default=Path(__file__).parent,
        help="Base directory containing templates and examples"
    )
    parser.add_argument(
        "--examples-dir",
        type=Path,
        default=None,
        help="Override examples directory (default: base_dir/examples)"
    )
    parser.add_argument(
        "--enable-search-tool",
        action="store_true",
        help="Enable the search_materials.py tool in generated environments (disabled by default)"
    )
    parser.add_argument(
        "--multiphase",
        action="store_true",
        help="Generate multi-phase meta-task (Phase 1: design category + scenario templates, Phase 2: generate task)"
    )
    parser.add_argument(
        "--topic", "-t",
        nargs="+",
        help="Specify topic(s) for multiphase mode. If fewer topics than --count, remaining tasks use random topics."
    )

    args = parser.parse_args()

    generator = MetaTaskGenerator(args.base_dir, examples_dir=args.examples_dir)

    # List mode
    if args.list:
        print("Available Scenarios:")
        for s in generator.list_scenarios():
            print(f"  - {s}")
        print("\nAvailable Categories:")
        for c in generator.list_categories():
            print(f"  - {c}")
        print("\nAvailable Examples:")
        for e in generator.list_examples():
            print(f"  - {e}")
        return

    # Generate mode
    if not args.output:
        parser.error("--output is required for generation")

    # Resolve topic list
    topics = args.topic if args.topic else []

    if args.count > 1:
        # Batch generation — auto-detect starting index to avoid overwriting
        base_output = args.output
        existing = [
            d.name for d in base_output.iterdir()
            if d.is_dir() and d.name.startswith("meta-task-")
        ] if base_output.exists() else []
        start_idx = 0
        for name in existing:
            try:
                idx = int(name.split("-")[-1])
                start_idx = max(start_idx, idx + 1)
            except ValueError:
                pass
        for i in range(args.count):
            output_dir = base_output / f"meta-task-{start_idx + i:04d}"
            seed = (args.seed + i) if args.seed else None
            # Use specified topic if available for this index, else None (random)
            task_topic = topics[i] if i < len(topics) else None
            try:
                result = generator.generate(
                    output_dir=output_dir,
                    scenario=args.scenario if i == 0 else None,  # Only first uses specified
                    category=args.category if i == 0 else None,
                    examples=args.examples if i == 0 else None,
                    difficulty=args.difficulty,  # Always use specified difficulty
                    seed=seed,
                    enable_search_tool=args.enable_search_tool,
                    multiphase=args.multiphase,
                    topic=task_topic
                )
                print(f"Generated: {result}")
            except Exception as e:
                print(f"Error generating {output_dir}: {e}", file=sys.stderr)
    else:
        # Single generation
        task_topic = topics[0] if topics else None
        try:
            result = generator.generate(
                output_dir=args.output,
                scenario=args.scenario,
                category=args.category,
                examples=args.examples,
                difficulty=args.difficulty,
                seed=args.seed,
                enable_search_tool=args.enable_search_tool,
                multiphase=args.multiphase,
                topic=task_topic
            )
            print(f"Generated meta-task at: {result}")

            # Print summary
            metadata_file = result / "generation_metadata.json"
            if metadata_file.exists():
                metadata = json.loads(metadata_file.read_text())
                print(f"  Scenario: {metadata['scenario']}")
                print(f"  Category: {metadata['category']}")
                print(f"  Difficulty: {metadata['difficulty']}")
                print(f"  Examples: {metadata['examples']}")
                if metadata.get('phase1_input_mode'):
                    print(f"  Phase1 Mode: {metadata['phase1_input_mode']}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
