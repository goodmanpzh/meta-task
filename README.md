# Meta-Task

*A compositional generator for terminal-agent tasks.*

Meta-Task is a **task generator that generates tasks**. Instead of writing terminal-agent
tasks by hand, we generate a *meta-task*: a self-contained prompt + environment that
instructs an AI agent to author a brand-new, self-verifying terminal task. Running the
meta-tasks through an agent harness (e.g. [Harbor](https://www.harborframework.com/))
yields a diverse corpus of terminal-agent tasks, each packaged as a Docker environment
with a programmatic verifier.

Each meta-task is assembled as an **independent product of structured axes** — a
*scenario* (writing style), a *category* (technical domain), a *difficulty*, and one or
more real *example* tasks — so the resulting task distribution is broad and controllable.

## What's here

| Path | What it is |
|------|------------|
| `generate_meta_task.py` | The generator. Combines templates/examples into a ready-to-run meta-task. |
| `templates/` | The sampling axes: `scenarios/` (10 writing styles), `categories/` (39 domains), `difficulty/` (easy/medium/hard/extreme), and the prompt templates. |
| `examples/` | Real, completed terminal tasks bundled into each meta-task as references. |
| `base/` | `Dockerfile.template`, `task.toml.template`, test templates, and `search_materials.py` (an optional in-container tool for pulling real GitHub/HF materials). |
| `review/` | Optional LLM-as-judge scripts for static quality review of generated tasks and trajectories. |

## Quickstart

Requires Python 3.10+. The generator uses only the Python standard library — no extra
dependencies.

```bash
git clone https://github.com/goodmanpzh/meta-task.git
cd Meta-Task

# List every available scenario / category / example
python generate_meta_task.py --list
```

### Single-phase generation

One agent turn: the meta-task hands the agent a fully-assembled prompt and it writes a task.

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

Two agent turns: Phase 1 designs the category/scenario templates from a sampled topic,
Phase 2 uses them to generate the task. Adds `--multiphase`; `--topic` optionally pins the topic.

```bash
python generate_meta_task.py --output ./output/mp --count 10 --multiphase
python generate_meta_task.py --output ./output/mp --multiphase --topic "log parsing"
```

### Key options

| Flag | Description |
|------|-------------|
| `--output, -o` | Output directory (required). |
| `--count, -n` | Number of meta-tasks to generate. |
| `--scenario, -s` | Pin the scenario (default: uniform random). |
| `--category, -c` | Pin the category (default: uniform random). |
| `--difficulty, -d` | `easy` / `medium` / `hard` / `extreme` (default: random medium/hard). |
| `--multiphase` | Two-phase generation (design templates, then generate). |
| `--topic, -t` | Topic(s) to anchor multi-phase generation. |
| `--enable-search-tool` | Inject `search_materials.py` into the environment. |
| `--seed` | Seed for reproducible sampling. |

## Running meta-tasks with an agent harness

A meta-task is just a standard terminal-agent task, so you can run it with any harness.
With Harbor, point it at the generated meta-task directory and pick an agent (e.g.
`claude-code` or `codex`):

```bash
harbor run \
    --path ./output/batch \
    --agent claude-code \
    --model "<model-name>" \
    --n-concurrent <N> \
    --job-name <job-name> \
    --force-build
```

> Configure your own model, endpoint/credentials, and concurrency for your environment.
> Set the agent to `claude-code`, `codex`, or any harness-supported agent.

### Extracting the generated tasks

The agent writes its finished task into the container at `/app/output/`, which Harbor
saves under the job's artifacts directory (e.g. `jobs/<job-name>/.../artifacts/generated-task/`).
Copy those artifacts out to the host to collect the generated corpus. Keep only tasks that
contain the full set of required files:

```
<task>/
├── instruction.md
├── task.toml
├── environment/   (Dockerfile + any data)
├── solution/      (solve.sh)
└── tests/         (test.sh + test_outputs.py)
```

Each extracted task is a self-contained, verifiable terminal-agent task ready to be
solved and used for training or evaluation.

## Optional: LLM-as-judge review

`review/task_review.py` and `review/traj_review.py` run a static quality check over
generated tasks / solving trajectories via an OpenAI-compatible endpoint. Provide your
own endpoint and model. These scripts require the extra dependency in
`requirements.txt`:

```bash
pip install -r requirements.txt
python review/task_review.py --api-base <http://host:port/v1> --model <model-name> ...
```

## License

Released under the [Apache License 2.0](LICENSE).
