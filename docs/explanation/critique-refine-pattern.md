# Critique/Refine Pattern

The critique/refine pattern separates generation from validation by running a structured audit after a generation step. A fast model generates content, a thinking model critiques it against the upstream material, and a fast model applies targeted fixes. This catches errors that single-pass generation misses — dropped content, visual inconsistencies, text-density problems — without requiring expensive models for the initial generation.

In the shipped pipelines this pattern is used in one place: the infographic pipeline's optional **i2 critique loop**, enabled with `--critique` (off by default).

## Loop Structure

```
                ┌─────────────┐
                │   Generate   │  i2 (fast tier)
                └──────┬──────┘
                       │
              save versioned output
                       │
           ┌───────────┴───────────┐
           │   for round in rounds │
           │                       │
           │  ┌─────────────┐      │
           │  │   Critique   │     │  i2_critique (thinking tier)
           │  └──────┬──────┘     │
           │         │            │
           │  save versioned critique
           │         │            │
           │  _needs_refinement?  │
           │    no ──┤── yes      │
           │    │    │            │
           │  break  │            │
           │         ▼            │
           │  ┌─────────────┐    │
           │  │    Refine    │    │  i2_refine (fast tier)
           │  └──────┬──────┘    │
           │         │           │
           │  save versioned output
           │         │           │
           └─────────┴───────────┘
                     │
            save canonical output
            (task-i2-prompts.yaml)
```

When `--critique` is not set, the loop is bypassed entirely — the initial `i2` generation is saved as the canonical output.

## The `_needs_refinement()` Predicate

The critique task defines a `_needs_refinement()` function that inspects the structured critique output and returns `True` only if refinement is warranted. This enables early exit when the critique finds no actionable issues.

From `src/polyptych/tasks/task_i2_critique.py`:

```python
def _needs_refinement(critique: TaskI2Critique) -> bool:
    return any(
        pi.severity in ("critical", "important") for pi in critique.prompt_issues
    )
```

Only `critical` or `important` issues trigger refinement — `minor` issues are tolerated. This severity gate keeps the loop cheap: a clean run skips the refine call entirely.

## The Critique Model

The critique task returns a `TaskI2Critique` Pydantic model (`src/polyptych/models/infographic.py`):

| Field | Meaning |
|-------|---------|
| `prompt_issues` | Per-variant quality issues, each with `variant_number`, `issue_type`, `description`, `severity`, and a concrete `suggested_fix`. |
| `dropped_key_content` | Primary key points or striking visualizable data from i0 that no longer appear in the prompt (informational; only an issue when also flagged as a `coverage_gap`). |
| `overall_assessment` | Human-readable summary of prompt quality and priority fixes. |

`issue_type` is one of: `color_inconsistency`, `semantic_loss`, `coverage_gap`, `flow_mismatch`, `text_density`, `style_drift`, `vague_or_overloaded`.

The critic audits each i2 variant against three references: the **i0** content analysis (coverage), the **i1** design specification (entity/color consistency, flow), and the rendering quality tier (text density) — all before the expensive image-generation step.

## Model Tier Conventions

Critique uses the `thinking` tier (extended-reasoning models); generation and refinement use the `fast` tier. Critique needs careful source reasoning to catch errors; refinement applies targeted structural fixes. Configuration lives in `model_config.yaml` under the `tasks` key:

```yaml
tasks:
  i2: fast            # Image prompts — formulaic per-variant
  i2_critique: thinking   # Prompt audit — must catch what i2 missed
  i2_refine: fast          # Targeted prompt corrections
```

## Versioned File Naming

Each round saves versioned files alongside the canonical output, so the refinement process is inspectable:

| Step | Action | Filename |
|------|--------|----------|
| 1 | Generate | `task-i2-1-prompts.yaml` |
| 2 | Critique round 1 | `task-i2-1-critique.yaml` |
| 3 | Refine round 1 | `task-i2-2-prompts.yaml` |
| — | Canonical | `task-i2-prompts.yaml` |

## CLI Flags

| Flag | Effect |
|------|--------|
| `--critique` | Enable the i2 critique loop (off by default). Also available as `--pipeline-preset critique`. |
| `--critique-rounds N` | Number of critique-refine iterations (default 1, requires `--critique`). |

## Related Documentation

- [Multi-Agent Patterns](multi-agent-patterns.md) — Generator-Critic and Iterative Refinement patterns (abstract view)
- [Pipeline Architectures](pipeline-architectures.md) — the infographic pipeline's step sequence
- [CLI Reference](../reference/cli-reference.md) — full flag documentation
