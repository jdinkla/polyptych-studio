# Pipeline Tier Optimization — Thinking/Fast Tier Assignments

Every LLM task uses either a **fast** (cheap, non-reasoning) or **thinking** (reasoning-enabled) tier. The tier picks which model string a provider uses (see the `providers` block in `model_config.yaml`), so the same logical task costs more or less depending on its tier. This document captures the assignments for both shipped pipelines and the reasoning behind each.

Source of truth: `model_config.yaml` — the `tasks` map (tiers), `max_output_tokens` (per-task output caps), and `thinking_budget` (per-task reasoning budgets, for providers that support extended thinking).

## Slide pipeline

| Task | Tier | Max tokens | Reasoning |
|------|------|-----------|-----------|
| task1 | fast | default | Genre classification — pattern matching against signal checklists. |
| task2 | thinking | default | Source analysis — deep structural extraction (sections, metaphors, emotional arc). |
| task3 | fast | default | Structure planning — constrained output over the task2 analysis. |
| task4 | thinking | default | Content allocation — multi-source reasoning, mapping paragraphs to slides under a compression budget. |
| task5 | fast | default | Visual design — template-guided palette/typography decisions. |
| task6 | thinking | default (16,384 thinking budget) | Slide specification — integrates the five prior outputs into per-slide specs. |
| task7 | fast | 32,000 | Image prompts — formulaic per slide; the high token cap is for batch mode on 13+ slides. |

## Infographic pipeline

| Task | Tier | Max tokens | Reasoning |
|------|------|-----------|-----------|
| i0 | thinking | 16,000 | Content analysis — deep structural extraction (key points, data, relationships). |
| i1 | thinking | default | Design specification — creative layout, sectioning, and palette decisions. |
| i2 | fast | 16,000 | Image prompts — formulaic per variant; cap allows for multiple variants in one call. |
| i2_critique | thinking | 8,000 | Prompt audit (opt-in `--critique`) — must catch what the fast i2 step missed. |
| i2_refine | fast | 16,000 | Targeted prompt corrections — replaces the full `TaskI2Output`. |

## The general rule

The pattern across both pipelines is consistent:

- **Thinking tier** for steps that synthesize or reason across multiple inputs or make open-ended creative decisions: source analysis (task2), content allocation (task4), slide synthesis (task6), infographic analysis/design (i0/i1), and any critique step.
- **Fast tier** for steps that are classification, constrained transformation, or formulaic generation from already-structured input: genre (task1), structure (task3), design templating (task5), and per-item prompt generation (task7, i2, i2_refine).

Critique steps are always **thinking** and refine steps are always **fast** — critique needs careful source reasoning to catch errors; refinement applies targeted structural fixes from the critique's findings. See [Critique/Refine Pattern](../explanation/critique-refine-pattern.md).

## Shared tasks

| Task | Tier | Purpose |
|------|------|---------|
| enrichment | fast | Prompt enrichment — simple context rewrite used during prompt construction. |

## Overrides

- `--model` / `$POLYPTYCH_MODEL` forces every task onto a single model, ignoring tiers entirely.
- Per-provider model strings for each tier live under the `providers` key in `model_config.yaml`.
- `thinking_budget` applies only to providers that support extended thinking (currently Anthropic); fast-tier tasks get no thinking regardless.
