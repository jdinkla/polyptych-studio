# Documentation

This project's documentation is organized using the [Diátaxis framework](https://diataxis.fr/) into four categories: tutorials, how-to guides, reference, and explanation.

Polyptych ships two pipelines: a **slide** deck pipeline (subcommand `deck`) and a single-page **infographic** pipeline (subcommand `infographic`).

## Tutorials

Step-by-step lessons for newcomers.

- [Your First Pipeline](tutorials/first-pipeline.md) — run the infographic and slide pipelines from scratch

## How-to Guides

Task-oriented recipes for specific goals.

- [Write Style Prompts](how-to/write-style-prompts.md) — author style-transfer presets for the `--style` flag
- [Resume a Pipeline](how-to/resume-pipeline.md) — resume failed or interrupted pipelines

## Reference

Technical descriptions of the system's machinery.

- [CLI Reference](reference/cli-reference.md) — commands, flags, env vars, pipeline task tables, just targets
- [TextClient API](reference/text-client-api.md) — multi-provider text generation API
- [Pipeline Tier Optimization](reference/pipeline-tier-optimization.md) — fast vs. thinking tier assignments per task

## Explanation

Understanding-oriented discussion of architecture and design decisions.

- [Operating Modes](explanation/operating-modes.md) — Python CLI vs Claude Code skills, and when to use which
- [System Overview](explanation/system-overview.md) — slide pipeline architecture
- [Pipeline Architectures](explanation/pipeline-architectures.md) — infographic pipeline internals and shared infrastructure
- [Task Decomposition](explanation/task-decomposition.md) — slide pipeline tasks 1–7
- [Critique/Refine Pattern](explanation/critique-refine-pattern.md) — the infographic critique loop and how the pattern works
- [Multi-Agent Patterns](explanation/multi-agent-patterns.md) — the pipelines viewed through multi-agent pattern lenses
