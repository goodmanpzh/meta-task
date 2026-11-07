# Meta-Task

[![arXiv](https://img.shields.io/badge/arXiv-2607.27929-b31b1b.svg)](https://arxiv.org/abs/2607.27929)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)

**Turning terminal task synthesis into a terminal task for scalable agent training.**

This is the official implementation of the paper
*Meta-Task: Turning Terminal Task Synthesis into a Terminal Task for Scalable Agent Training*
([arXiv:2607.27929](https://arxiv.org/abs/2607.27929)).

## Overview

Training terminal agents at scale needs diverse, verifiable terminal tasks and high-quality
interaction trajectories. Meta-Task generates both by **redefining task synthesis as a
Terminal-Bench-format task itself**: instead of separately producing instructions, environments,
solutions and tests, each synthesis request is packaged as a *meta-task* — a standard task
package whose instruction asks an agent to author a brand-new, self-verifying terminal task.

An agent runs the meta-task inside a Docker container, explores reference examples, optionally
retrieves real materials, designs and implements a complete task package, and iteratively
validates its output until the built-in checks pass. Because generation and execution happen in
the same live container, synthesized tasks are grounded in real command output rather than pure
text generation.

```
┌─────────────────────┐   ┌─────────────────────┐   ┌──────────────────────┐
│  Meta-Task          │   │  Agent Synthesis    │   │  Quality Filtering   │
│  Generation         │──▶│  (Harbor + scaffold)│──▶│  (execution + judge) │
│  this repo          │   │  generates tasks    │   │  review/             │
└─────────────────────┘   └─────────────────────┘   └──────────────────────┘
```

Diversity is controlled along three orthogonal axes — **category** (technical domain, 39
templates), **scenario** (instruction writing style, 10 templates) and **difficulty**
(easy / medium / hard / extreme) — giving 39 × 10 × 4 = 1,560 base combinations in
single-phase mode. **Multi-phase** mode instead has the agent design novel category/scenario
specifications from sampled topic and style seeds before writing the task.

## Results

Fine-tuning on **3,221** Meta-Task synthesized trajectories, evaluated on **Terminal-Bench 2.0**
with the Terminus-2 scaffold (Avg Pass@1):

| Model | Base | Meta-Task | Without training |
|-------|-----:|----------:|-----------------:|
| [Meta-Task-14B](https://huggingface.co/saulpzh/Meta-Task-14B) | Qwen3-14B | **22.5 %** | 5.2 % |
| [Meta-Task-32B](https://huggingface.co/saulpzh/Meta-Task-32B) | Qwen3-32B | **31.8 %** | 4.1 % |

These results use substantially fewer trajectories than comparable synthesis pipelines
(e.g. 50.7 K for TerminalTraj, 490.5 K for Nemotron-Terminal).

## Released artifacts

| Artifact | Link | Size |
|----------|------|------|
| Meta-Task-14B (Qwen3-14B fine-tuned) | [saulpzh/Meta-Task-14B](https://huggingface.co/saulpzh/Meta-Task-14B) | 29.6 GB |
| Meta-Task-32B (Qwen3-32B fine-tuned) | [saulpzh/Meta-Task-32B](https://huggingface.co/saulpzh/Meta-Task-32B) | 65.5 GB |
| Generated tasks + SFT trajectories | [saulpzh/Meta-Task-Data](https://huggingface.co/datasets/saulpzh/Meta-Task-Data) | 0.9 GB |

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_id = "saulpzh/Meta-Task-32B"  # or saulpzh/Meta-Task-14B
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype="bfloat16", device_map="auto")
```

The dataset repository contains:

| Path | Contents |
|------|----------|
| `tasks/meta_tasks_v1.tar.gz` | 3,220 synthesized terminal tasks, each a complete Terminal-Bench package (`instruction.md`, `task.toml`, `environment/`, `solution/`, `tests/`). Extracts to `v1/<task-name>/`. |
| `trajectories/sft_trajectories_3221.jsonl` | 3,221 SFT trajectories (`messages`, `id`, `data_type`, `special_ability`, `source`, `synthetic_model`, `tag`), one JSON object per line. |

## Installation

Python 3.10+ is required. The generator uses only the Python standard library.

```bash
git clone https://github.com/goodmanpzh/meta-task.git
cd meta-task

# Only needed for the optional LLM-as-judge scripts in review/
pip install -r requirements.txt
```

## Usage

### List available axes

```bash
python generate_meta_task.py --list
```

Prints every scenario, category and bundled example.

### Single-phase generation

The meta-task hands the agent a fully-assembled prompt, and the agent writes the task.

```bash
# Fully random (uniform over scenarios / categories)
python generate_meta_task.py --output ./output/task_001

# Pin any axis
python generate_meta_task.py --output ./output/task_002 \
    --category debugging --scenario narrative --difficulty hard

# Batch (auto-indexed meta-task-0000, meta-task-0001, ...)
python generate_meta_task.py --output ./output/batch --count 10 --difficulty hard

# Enable the in-container material-search tool (off by default)
python generate_meta_task.py --output ./output/task_003 --enable-search-tool
```

### Multi-phase generation

Two agent turns: Phase 1 designs a new category/scenario specification from sampled topic and
style seeds; Phase 2 uses that specification to generate the task.

```bash
python generate_meta_task.py --output ./output/mp --count 10 --multiphase
python generate_meta_task.py --output ./output/mp --multiphase --topic "log parsing"
```

### Key options

| Flag | Description |
|------|-------------|
| `--output, -o` | Output directory. Required for generation, not needed with `--list`. |
| `--count, -n` | Number of meta-tasks to generate (default: 1). |
| `--scenario, -s` | Pin the scenario (default: uniform random). |
| `--category, -c` | Pin the category (default: uniform random). |
| `--difficulty, -d` | `easy` / `medium` / `hard` / `extreme` (default: random `medium` or `hard`). |
| `--examples, -e` | Explicit example task paths to bundle (default: one randomly sampled from `examples/`). |
| `--multiphase` | Two-phase generation (design a specification, then generate the task). |
| `--topic, -t` | Topic(s) to anchor multi-phase generation. |
| `--enable-search-tool` | Inject `search_materials.py` into the generated environment. |
| `--seed` | Seed for reproducible sampling. |
| `--base-dir, -b` | Directory containing `templates/` and `examples/` (default: the script's directory). |
| `--examples-dir` | Override the examples directory. |
| `--list, -l` | List available scenarios, categories and examples. |

## Running meta-tasks

A meta-task is a standard Terminal-Bench-format task, so any harness that supports that format
can execute it. In our experiments we use [Harbor](https://www.harborframework.com/) as the
**orchestration framework** — it schedules meta-task execution and collects the outputs —
together with an **agent scaffold** such as Claude Code, Codex CLI or Terminus-2 that performs
the actual synthesis:

```bash
harbor run \
    --path ./output/batch \
    --agent claude-code \
    --model "<model-name>" \
    --n-concurrent <N> \
    --job-name <job-name> \
    --force-build
```

> `--agent` selects the scaffold (`claude-code`, `codex`, `terminus-2`, …); Harbor itself is the
> orchestration layer, not the agent. Configure your own model, endpoint and concurrency, and see
> Harbor's documentation for the current CLI.

### Extracting the generated tasks

The agent writes its finished task into the container at `/app/output/`, which Harbor saves under
the job's artifacts directory (e.g. `jobs/<job-name>/.../artifacts/`). Copy those artifacts out
to the host and keep the tasks that contain the full set of required files:

```
<task>/
├── instruction.md
├── task.toml
├── environment/   (Dockerfile + any data)
├── solution/      (solve.sh)
└── tests/         (test.sh + test_outputs.py)
```

Each extracted task is a self-contained, verifiable terminal task ready for training or
evaluation.

## Optional: LLM-as-judge review

`review/task_review.py` and `review/traj_review.py` run a static quality check over generated
tasks or solving trajectories through an OpenAI-compatible endpoint. Provide your own endpoint
and model:

```bash
python review/task_review.py \
    --source ./generated/tasks \
    --api-base <http://host:port/v1> \
    --model <model-name>
```

## Repository structure

| Path | Contents |
|------|----------|
| `generate_meta_task.py` | The generator. Composes templates, examples and base files into a ready-to-run meta-task. |
| `templates/` | `categories/` (39 domains), `scenarios/` (10 writing styles), `difficulty/` (4 levels), `case_template/` (output skeleton), the prompt templates, and the multi-phase seed lists (`topics.txt`, `scenario_dimensions.txt`). |
| `examples/` | A pool of reference terminal tasks (synthesized and manually verified). One is sampled per meta-task by default. |
| `base/` | `Dockerfile.template`, `task.toml.template`, test templates, `assemble_prompt.py`, and `search_materials.py` (an optional in-container tool for retrieving GitHub / Hugging Face materials). |
| `review/` | Optional LLM-as-judge scripts for quality review of generated tasks and solving trajectories. |

## Citation

If you use this code, the models or the synthesized data, please cite:

```bibtex
@article{pan2026metatask,
  title   = {Meta-Task: Turning Terminal Task Synthesis into a Terminal Task for Scalable Agent Training},
  author  = {Pan, Zhihong and He, Jiyuan and Zhang, Kai and Han, Yupeng and
             Liu, Ze and Zhao, Yuze and Ye, Yongcong and Yang, Zhaohua},
  journal = {arXiv preprint arXiv:2607.27929},
  year    = {2026}
}
```

## License

Released under the [Apache License 2.0](LICENSE).
