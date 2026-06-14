# Your First Pipeline

This tutorial walks you through running your first pipeline, examining the outputs, and trying a style preset. By the end, you'll understand the basic workflow shared by both pipelines (slide and infographic).

## Prerequisites

1. **Install dependencies:**

   ```bash
   uv sync
   ```

2. **Set up an API key** for at least one text provider (Gemini recommended):

   ```bash
   export GOOGLE_API_KEY="your-gemini-api-key"
   ```

3. **Have a source essay** — any markdown file works. An example ships at
   `examples/scene.md` (a short noir scene, good for the slide pipeline's
   fiction path); or create your own:

   ```bash
   cat > /tmp/sample-essay.md << 'EOF'
   # The Architecture of Morning Coffee

   There is a quiet engineering to the first cup of coffee. The kettle reaches
   precisely 96 degrees — not boiling, never boiling — because the difference
   between 96 and 100 is the difference between extraction and destruction.

   The grounds sit in their paper filter like sediment waiting for a river. When
   the water hits, it doesn't rush. It finds channels, carves paths through the
   packed earth of dark roast, pulls oils and acids into solution with the patience
   of geology compressed into four minutes.

   Most people think coffee is about caffeine. It isn't. It's about the ritual of
   transformation: solid to liquid, potential to kinetic, silence to the first sip
   that says the day has officially begun.

   The Japanese have a word for this — *komorebi* isn't quite right, but the
   concept of light filtering through leaves captures something similar. Coffee
   filters light too, in its way. Hold a cup to the window and watch amber shift
   to mahogany at the edges. That gradient is the morning's first lesson in
   complexity: even the simplest things contain multitudes.
   EOF
   ```

## Step 1: Run the Infographic Pipeline

The infographic pipeline is the simplest — three text tasks plus image generation. Start here.

```bash
uv run polyptych infographic /tmp/sample-essay.md -o /tmp/coffee-infographic
```

This runs three tasks:
- **i0** — Analyzes the essay content (key points, data, relationships)
- **i1** — Designs the infographic layout (sections, color palette, visual style)
- **i2** — Generates image prompts (3 variants by default)

Then it generates images via your configured provider.

**Text tasks only** (skip image generation to save API costs while learning):

```bash
uv run polyptych infographic /tmp/sample-essay.md -o /tmp/coffee-infographic --to i2
```

## Step 2: Examine the Output

Look at the generated YAML files:

```bash
ls /tmp/coffee-infographic/
```

You'll see files like:
- `task-i0-analysis.yaml` — structured content analysis
- `task-i1-design.yaml` — design specification
- `task-i2-prompts.yaml` — image generation prompts

Read any of them to see the structured output:

```bash
cat /tmp/coffee-infographic/task-i0-analysis.yaml
```

Each file is a validated Pydantic model serialized as YAML — human-readable and machine-parseable.

## Step 3: Validate the Output

The CLI includes a validation command that checks outputs against their schemas:

```bash
uv run polyptych validate /tmp/coffee-infographic
```

This confirms all task outputs parse correctly against their Pydantic models.

## Step 4: Run the Slide Pipeline

Now try the full slide pipeline — more steps, richer output:

```bash
uv run polyptych deck /tmp/sample-essay.md -o /tmp/coffee-slides --to task7
```

This runs seven tasks:
1. Genre classification
2. Source analysis
3. Structure planning
4. Content allocation
5. Visual design specification
6. Slide specification
7. Image prompt generation

Examine the genre detection:

```bash
cat /tmp/coffee-slides/task1-genre.yaml
```

## Step 5: Try a Style Preset

Style presets customize the visual aesthetic. They're markdown files in `prompts/style-transfer/`:

```bash
ls prompts/style-transfer/
```

Try running with a style:

```bash
uv run polyptych deck /tmp/sample-essay.md -o /tmp/coffee-noir \
  --style prompts/style-transfer/noir/cinematic-illustrative-noir.md --to task7
```

Compare the task-07 prompts between the default and noir runs to see how style affects prompt generation.

## Step 6: Use Just Targets

The `justfile` provides shortcuts for common workflows:

```bash
just --list
```

Most pipeline operations have `just` targets that save typing. Check the [CLI Reference](../reference/cli-reference.md) for the full list.

## What's Next

- **[CLI Reference](../reference/cli-reference.md)** — full command documentation for both pipelines
- **[Write Style Prompts](../how-to/write-style-prompts.md)** — create custom visual styles
- **[Resume a Pipeline](../how-to/resume-pipeline.md)** — resume interrupted runs or regenerate specific items
- **[System Overview](../explanation/system-overview.md)** — understand the slide pipeline architecture
- **[Pipeline Architectures](../explanation/pipeline-architectures.md)** — infographic pipeline internals
