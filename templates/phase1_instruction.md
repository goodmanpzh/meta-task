# Phase 1: Generate a New Category and Scenario

You are a creative task designer. Your job is to generate a **category template** and a **scenario template** that will guide the creation of a terminal-based evaluation task — a task where an AI agent works in a Linux Docker container, using the terminal to accomplish goals through code, commands, and tools.

These tasks test an agent's ability to **plan, explore, and accomplish goals** — given a goal (sometimes vague), the agent must figure out how to achieve it by exploring the environment and making decisions on its own.

**Target difficulty: $difficulty.**

$difficulty_requirements

Your task patterns and examples should reflect this difficulty level. Your output is a starting point that another agent will build on, so aim for diversity and creativity.

---

## Your Topic: **$topic**

Generate a category template around this topic. Below is a reference category template (on a different topic) showing the format and level of detail to aim for:

```markdown
$category_ref
```

## Reference Scenario Template

Below is an example scenario template showing the format. Generate a **new** scenario template with a different style.

```markdown
$scenario_ref
```

---

## Your Task

Write your output to the file `/app/phase1_output.md` (you must actually create and write this file, not just output to stdout) containing a new category (around the topic **$topic**) and a new scenario.

**For the category:** Build around **$topic** — come up with diverse task patterns, tools, data types, and challenges specific to this topic. Use the reference above only for format guidance.

**For the scenario:** Your scenario must follow this constraint:

> **$scenario_constraint**

Design a scenario template that produces instruction.md files matching the constraint above. The scenario should specify the writing style, detail level, tone, and information strategy. Use the reference scenario template above only for format guidance — the actual style should match the constraint.

```
=== CATEGORY ===

### Category: [Name]

[Your category content — same format as the reference]

=== SCENARIO ===

For the `instruction.md` you generate, use a **[style name]** style:

[Your scenario content — same format as the reference]
```

**Keep similar length to the references.** Don't write much more or much less than what you see above.
