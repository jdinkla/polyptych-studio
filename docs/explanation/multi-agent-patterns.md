# Multi-Agent Patterns in This Repository

An analysis of this system's architecture through the lens of [Google's multi-agent patterns in ADK](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/). The blog post identifies seven canonical patterns for multi-agent systems. The two shipped pipelines (slide and infographic) implement several of them — some by design, some emergent from practical engineering needs.

## Pattern Mapping Summary

| ADK Pattern | Present? | Where |
|---|---|---|
| Sequential Pipeline | Yes (primary) | Both pipelines |
| Coordinator / Dispatcher | Yes | CLI dispatch, provider routing, genre routing |
| Hierarchical Decomposition | Yes | SlidePipeline → task functions → provider calls |
| Generator and Critic | Yes | Infographic i2 critique loop (opt-in) |
| Iterative Refinement | Yes | i2 multi-round critique with early exit |
| Human-in-the-Loop | Partial | CLI resume, `--from`, `--slides` targeting |

---

## 1. Sequential Pipeline (Assembly Line)

**ADK definition:** Linear workflow where each agent's output becomes the next agent's input, with state managed through shared session state.

**This system's implementation:** The foundational pattern. Each pipeline is a strict DAG of LLM tasks where every step produces a YAML file consumed by downstream steps. The "shared session state" is the filesystem — each task writes a validated Pydantic output to a `task-*.yaml` file, and downstream tasks load those files as input context.

### Slide pipeline (7 steps)

```
essay.md → task1(genre) → task2(analysis) → task3(structure) → task4(content)
         → task5(design) → task6(slides) → task7(prompts) → images
```

### Infographic pipeline (3 steps)

```
source.md → i0(analysis) → i1(design) → i2(prompts) → images
```

Step dependencies are declared explicitly in `pipeline_config.py` (`STEP_DEPENDENCIES`, `INFOGRAPHIC_STEP_DEPENDENCIES`). Before a step runs, its required upstream YAMLs must exist and parse.

### Key properties matching the ADK pattern

- **Deterministic flow:** Steps execute in fixed order. The DAG is enforced, not discovered at runtime.
- **Easy to debug:** Each step writes a named YAML file, creating a complete audit trail. Intermediate outputs are human-readable.
- **Checkpoint/resume:** `find_resume_step()` walks the step list, validates each output against its Pydantic model, and returns the first missing or invalid step — making the pipeline idempotent.

### Divergence from ADK

ADK uses in-memory `session.state` with `output_key` per agent. This system uses **YAML files on disk** as the state medium. More robust (crash-safe, inspectable, resumable) but introduces filesystem coupling that in-memory state avoids.

---

## 2. Coordinator / Dispatcher (Concierge)

**ADK definition:** A central intelligent agent analyzes intent and routes requests to specialist agents.

**This system's implementation:** Three levels of dispatch, ranging from code-driven to LLM-driven.

### Level 1: CLI dispatch (code-driven)

The CLI entry point (`cli.py`) routes to the appropriate pipeline:

```
polyptych deck        → run_from()                  (slide)
polyptych infographic → run_infographic_pipeline()
```

A hard-coded coordinator — no LLM routing, just CLI argument matching. The user acts as the intelligent router.

### Level 2: Provider routing (code-driven with fallback)

`TextClient.generate_structured()` implements a try-primary-then-fallback dispatch chain:

```
TextClient.generate_structured(prompt, schema, model, task=...)
├── try: primary_provider.generate_structured(...)
│   └── on ContentBlockedError / TransientProviderError → log + fallback
└── for fb in _fallback_chain:
    └── try: fb_provider.generate_structured(fb_model, ...)
        └── on error → log + try next
```

The fallback chain is configured at construction time (e.g. Gemini → OpenAI → xAI). Each fallback uses `model_resolver` to select the correct model for that provider + task tier. This resembles ADK's coordinator routing to specialists, though triggered by failure rather than intent analysis.

### Level 3: Genre-based prompt routing (LLM-driven, slide only)

Task 1 classifies the source essay into a genre. Task 6 uses the genre to select a prompt variant:

```python
# prompt_loader.py
if genre and task_number == 6:
    variant_file = f"task-06-slide-specification-{genre}.md"
    if variant_file.exists():
        return variant_file.read_text()
```

This is the closest match to ADK's pattern: an LLM agent (Task 1) produces a classification that drives a downstream routing decision.

### Divergence from ADK

ADK's coordinator uses `AutoFlow` with LLM-driven delegation based on sub-agent descriptions. This system's routing is mostly deterministic (CLI args, fallback order) with one LLM-driven decision (genre classification), embedded in control flow rather than being a first-class agent role.

---

## 3. Hierarchical Decomposition (Russian Doll)

**ADK definition:** High-level agents break complex goals into sub-tasks and delegate them.

**This system's implementation:** Three-level hierarchy.

```
SlidePipeline (orchestrator)
├── run_task_01() → task_01_genre.run_task_01() → TextClient → Provider
├── run_task_02() → task_02_analysis.run_task_02() → TextClient → Provider
├── ...
└── _generate_images() → ImageClient → ImageProvider
```

### Level 1: Pipeline orchestrator

Owns control flow, dependency validation, resume logic, and state management. Delegates LLM work downward.

### Level 2: Task functions (specialist agents)

Pure functions in `src/polyptych/tasks/`. Each loads a prompt template, injects context, calls `TextClient.generate_structured()`, and returns a validated Pydantic model. Tasks are stateless — they don't know about the pipeline or other tasks.

### Level 3: Provider calls (execution layer)

`TextClient` resolves the model tier, selects the provider, and handles fallback. Providers handle API-specific serialization, response parsing, and JSON repair.

### Divergence from ADK

ADK wraps sub-agents as `AgentTool` objects callable by the parent's LLM. Here, the decomposition is coded by the developer, not discovered by an LLM. The pipeline structure is fixed at design time.

---

## 4. Generator and Critic (Editor's Desk) + Iterative Refinement (Sculptor)

**ADK definition:** Separate content creation from validation. A generator produces drafts; a critic reviews against criteria with conditional looping until quality is sufficient, with early exit.

**This system's implementation:** The infographic pipeline's optional **i2 critique loop** (`--critique`, off by default).

```
i2_output = run_task_i2(...)                  # Generator (fast tier)
for round in range(critique_rounds):
    critique = run_task_i2_critique(i0, i1, i2_output)   # Critic (thinking tier)
    if not _needs_refinement(critique):
        break                                 # Quality gate: pass
    i2_output = run_task_i2_refine(i2_output, critique)  # Refine (fast tier)
save(i2_output)
```

- **Role separation.** Generation and refinement use the `fast` tier for speed; critique uses the `thinking` tier for depth — mirroring ADK's separation of creation and validation.
- **Severity-gated early exit.** `_needs_refinement()` returns `True` only for `critical`/`important` issues. Clean prompts skip the refine call, saving LLM cost — matching ADK's `escalate=True` early-exit mechanism.
- **Structured audit.** The critic doesn't get a vague "review this"; it audits each i2 variant against the i0 content analysis (coverage), the i1 design spec (consistency, flow), and the rendering tier (text density), returning a typed `TaskI2Critique`.

See [Critique/Refine Pattern](critique-refine-pattern.md) for the full mechanics.

### Divergence from ADK

ADK uses `LoopAgent` as a declarative primitive with a pass/fail gate. This system implements the loop imperatively with `for round in range(critique_rounds)`. The round count is configurable via `--critique-rounds`, and the early-exit condition examines the typed critique output rather than a binary flag.

---

## 5. Human-in-the-Loop (Safety Net)

**ADK definition:** Agents handle groundwork, but humans authorize critical decisions before execution.

**This system's implementation:** Partial. The pipeline doesn't pause mid-run for approval, but provides several human-control mechanisms between runs.

- **Resume control (`--from`).** Start from any step. Combined with auto-resume (`--from auto`), inspect intermediate YAML between runs and proceed only when satisfied.
- **Selective regeneration (`--slides`).** After image generation, inspect results and regenerate specific slides: `--slides 3,7,12`.
- **Style and model overrides.** `--style`, `--model`, `--provider` override the system's automatic choices — design-time decisions rather than runtime approval gates.

### Divergence from ADK

ADK's pattern involves runtime execution pauses with approval workflows. This system's human control is **between runs**, not during execution.

---

## Composite Patterns: How the Pipelines Combine Them

### Slide pipeline

```
Sequential Pipeline (7 steps)
  + Coordinator/Dispatcher (genre routing at task 6, provider fallback)
  + Hierarchical Decomposition (pipeline → tasks → providers)
```

A linear flow with one LLM-driven routing decision.

### Infographic pipeline

```
Sequential Pipeline (3 steps + images)
  + Hierarchical Decomposition
  + Generator-Critic / Iterative Refinement (i2 loop, when --critique)
```

Pure linear by default; with `--critique` it gains a generator-critic loop on the prompt step.

---

## Architectural Comparison

| Dimension | ADK Approach | This System |
|---|---|---|
| Agent definition | `Agent` classes with descriptions | Pure functions in `tasks/` |
| Composition | Declarative (`SequentialAgent`, `LoopAgent`) | Imperative (Python control flow) |
| State medium | In-memory `session.state` with `output_key` | YAML files on disk |
| Routing | LLM-driven `AutoFlow` | Mostly code-driven; one LLM-driven routing (genre) |
| Critique loops | `LoopAgent` with pass/fail gate | Imperative `for` loop with `_needs_refinement()` |
| Provider abstraction | Not in scope (provider-agnostic) | Multi-provider with fallback chain |
| Resume/checkpoint | Not in scope | First-class: auto-resume from any step |
| Human-in-the-loop | Runtime `ApprovalTool` pause | Between-run inspection + selective re-run |

### What this system adds beyond ADK patterns

1. **YAML-as-checkpoint:** Persisted intermediate state enables resume, inspection, and debugging in ways in-memory state cannot.
2. **Provider fallback chains:** The text client's content-blocking / transient-error fallback is a resilience pattern not covered by ADK's agent patterns.
3. **Pydantic schema contracts:** Each task's output is validated against a typed schema, catching LLM output errors at the boundary.
4. **Truncated JSON repair:** `repair_truncated_json()` in `providers/base.py` handles models that hit `max_tokens` mid-output.
5. **Model tier separation:** Thinking models for critique, fast models for generation — configured per task in `model_config.yaml`.

---

## References

- [Developer's Guide to Multi-Agent Patterns in ADK](https://developers.googleblog.com/developers-guide-to-multi-agent-patterns-in-adk/) — Google Developers Blog
- `src/polyptych/pipeline.py` — pipeline orchestration
- `src/polyptych/client.py` — TextClient with fallback chain
- `src/polyptych/concurrent_engine.py` — producer-consumer parallelism
- `model_config.yaml` — per-task model tier configuration
