# Task Decomposition: Slide Pipeline (Tasks 1–7)

## Overview

This document breaks down the 7-task **slide** pipeline into discrete, chainable tasks. Each task has defined inputs, outputs, and a clear purpose.

- Tasks 1–6: Transform essay into slide specifications
- Task 7: Transform slide specifications into Gemini-compatible image prompts

For the infographic pipeline's task structure, see [Pipeline Architectures](pipeline-architectures.md). Prompt files are zero-padded for the slide pipeline: `prompts/tasks/task-01-genre-classification.md`, `task-02-source-analysis.md`, etc. The on-disk output filenames are `task1-genre.yaml`, `task2-analysis.yaml`, … `task7-prompts.yaml`.

---

## Task Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            TASK PIPELINE                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────┐                                                                  │
│  │ SOURCE  │                                                                  │
│  │ ESSAY   │                                                                  │
│  └────┬────┘                                                                  │
│       │                                                                       │
│       ▼                                                                       │
│  ┌─────────────────────────────────────────┐                                  │
│  │           TASK 1: Genre Classification   │                                  │
│  │  Input:  Source essay                    │                                  │
│  │  Output: Genre label + parameters        │                                  │
│  └────────────────────┬────────────────────┘                                  │
│                       │                                                       │
│                       ▼                                                       │
│  ┌─────────────────────────────────────────┐                                  │
│  │           TASK 2: Source Analysis        │                                  │
│  │  Input:  Source essay + genre            │                                  │
│  │  Output: Structured analysis document    │                                  │
│  └────────────────────┬────────────────────┘                                  │
│                       │                                                       │
│                       ▼                                                       │
│  ┌─────────────────────────────────────────┐                                  │
│  │           TASK 3: Structure Planning     │                                  │
│  │  Input:  Analysis + genre                │                                  │
│  │  Output: Slide sequence with roles       │                                  │
│  └────────────────────┬────────────────────┘                                  │
│                       │                                                       │
│                       ▼                                                       │
│  ┌─────────────────────────────────────────┐                                  │
│  │           TASK 4: Content Allocation     │                                  │
│  │  Input:  Structure + analysis            │                                  │
│  │  Output: Per-slide content assignments   │                                  │
│  └────────────────────┬────────────────────┘                                  │
│                       │                                                       │
│                       ▼                                                       │
│  ┌─────────────────────────────────────────┐                                  │
│  │           TASK 5: Visual Design Spec     │                                  │
│  │  Input:  Genre + content allocation      │                                  │
│  │  Output: Design system rules             │                                  │
│  └────────────────────┬────────────────────┘                                  │
│                       │                                                       │
│                       ▼                                                       │
│  ┌─────────────────────────────────────────┐                                  │
│  │           TASK 6: Slide Specification    │                                  │
│  │  Input:  All previous outputs            │                                  │
│  │  Output: Complete per-slide specs        │                                  │
│  └────────────────────┬────────────────────┘                                  │
│                       │                                                       │
│                       ▼                                                       │
│  ┌─────────────────────────────────────────┐                                  │
│  │           TASK 7: Image Generation       │                                  │
│  │  Input:  Slide specs + design system     │                                  │
│  │  Output: Gemini-ready image prompts      │                                  │
│  └────────────────────┬────────────────────┘                                  │
│                       │                                                       │
│                       ▼                                                       │
│                 ┌───────────┐                                                 │
│                 │  IMAGE    │                                                 │
│                 │  PROMPTS  │                                                 │
│                 └─────┬─────┘                                                 │
│                       │                                                       │
│                       ▼                                                       │
│                 ┌───────────┐                                                 │
│                 │  GEMINI   │──────────────▶ [Generated Images]               │
│                 └───────────┘                                                 │
│                                                                               │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Task 1: Genre Classification

### Purpose
Determine the content type of the source essay to select appropriate downstream parameters.

### Input
```
source_essay: string (full markdown text)
```

### Output
```yaml
genre: "personal_essay" | "analytical_critique" | "policy_argument" | "fiction" | "strategic_diagnostic" | "conceptual_essay"
confidence: float (0-1)
parameters:
  compression_ratio: float
  structure_type: string
  metaphor_strategy: "distributed" | "unified" | "extended"
  color_system: "varied" | "strict_dichotomy" | "dual_accent"
  closing_strategy: "personal_action" | "imperative" | "human_return"
signals_detected:
  - signal_name: string
    evidence: string
```

### Classification Logic

**Personal Essay Signals**:
- First-person voice ("I," "my," "we")
- Sensory language (smell, touch, sound)
- Emotional reflection
- Narrative structure with personal stakes
- Lyrical/poetic phrasing

**Analytical Critique Signals**:
- Third-person or analytical voice
- Technical terminology
- Systematic argument structure
- Reference to external frameworks/standards
- Definitional precision

**Policy Argument Signals**:
- Systems vocabulary ("stock," "flow," "lag-time")
- Problem-solution structure
- Human stakes bookended around analysis
- Infrastructure/economic metaphors
- Diagnostic framing

**Fiction Signals**:
- Characters with names and dialogue
- Scene descriptions and action
- Narrative progression through events
- Sensory and environmental detail
- Point-of-view narration

**Strategic Diagnostic Signals**:
- Diagnostic framing of systems or organizations
- Strategic analysis vocabulary
- Assessment of current state vs. desired state
- Recommendations or prescriptions
- Evidence-based argumentation

### Example Output

```yaml
genre: "policy_argument"
confidence: 0.85
parameters:
  compression_ratio: 1.7
  structure_type: "5-part policy"
  metaphor_strategy: "extended"
  color_system: "dual_accent"
  closing_strategy: "human_return"
signals_detected:
  - signal_name: "systems_vocabulary"
    evidence: "Uses 'stock', 'flow', 'inflows', 'lag-time'"
  - signal_name: "human_bookending"
    evidence: "Opens and closes with 'young couple in coffee shop'"
  - signal_name: "infrastructure_metaphor"
    evidence: "Extended cistern/valve/pipe metaphor throughout"
```

---

## Task 2: Source Analysis

### Purpose
Extract raw materials from the source essay for slide generation.

### Input
```yaml
source_essay: string
genre: string (from Task 1)
```

### Output
```yaml
structural_analysis:
  sections:
    - id: string
      title: string (if present, else null)
      paragraphs: [int] (paragraph numbers)
      function: "introduction" | "body" | "conclusion" | "transition"

quotable_passages:
  - id: string
    text: string
    source_paragraph: int
    qualities:
      standalone: boolean
      aphoristic: boolean
      visualizable: boolean
      emotional_punch: boolean
    suggested_usage: "headline" | "body" | "callout" | "closing"

metaphor_inventory:
  dominant_metaphor:
    present: boolean
    description: string (if present)
    components: [string] (if extended metaphor)
  secondary_metaphors:
    - concept: string
      visual: string
      source_paragraph: int

emotional_arc:
  opening_energy: 1-5
  trajectory: [int] (energy level per section)
  peak_moments: [paragraph_id]
  nadir_moment: paragraph_id | null
  resolution_type: string

key_concepts:
  - concept: string
    importance: "primary" | "secondary"
    visualizable: boolean
```

### Example Output (abbreviated)

```yaml
structural_analysis:
  sections:
    - id: "intro"
      title: null
      paragraphs: [1, 2]
      function: "introduction"
    - id: "cistern"
      title: "The Cistern and the Valve"
      paragraphs: [3, 4, 5]
      function: "body"

quotable_passages:
  - id: "q1"
    text: "The ink on the check dries in seconds; the concrete in a foundation takes a season."
    source_paragraph: 2
    qualities:
      standalone: true
      aphoristic: true
      visualizable: true
      emotional_punch: true
    suggested_usage: "callout"

metaphor_inventory:
  dominant_metaphor:
    present: true
    description: "Water infrastructure as economic system"
    components: ["cistern", "valve", "inflows", "pressure", "flow"]
  secondary_metaphors:
    - concept: "demographic stagnation"
      visual: "ice/frozen"
      source_paragraph: 13
```

---

## Task 3: Structure Planning

### Purpose
Determine slide count, sequence, and role assignment based on genre and analysis.

### Input
```yaml
source_analysis: (from Task 2)
genre: string
parameters: (from Task 1)
```

### Output
```yaml
slide_count: int
slide_sequence:
  - slide_number: int
    role: string
    source_section: string
    intensity: 1-5
    notes: string

arc_visualization:
  type: string ("3-act" | "4-part" | "5-part")
  peaks: [slide_number]
  nadir: slide_number | null
  concession: slide_number | null
```

### Role Vocabulary

| Role | Description |
|------|-------------|
| `title` | Opening slide with title and hook |
| `hook` | Establish emotional/intellectual stakes |
| `build` | Develop argument or narrative |
| `peak` | Maximum intensity moment |
| `nadir` | Lowest emotional point |
| `concession` | Acknowledge counterargument |
| `reframe` | Shift perspective |
| `transition` | Bridge between sections |
| `evidence` | Support with example or data |
| `resolution` | Provide closure |

### Example Output

```yaml
slide_count: 15
slide_sequence:
  - slide_number: 1
    role: "title"
    source_section: "intro"
    intensity: 3
    notes: "Magazine format with issue badge"
  - slide_number: 2
    role: "hook"
    source_section: "intro"
    intensity: 3
    notes: "Coffee shop couple - human stakes"
  - slide_number: 7
    role: "peak"
    source_section: "lag-time"
    intensity: 4
    notes: "Historical revelation - diagnosis peak"
  - slide_number: 12
    role: "peak"
    source_section: "ai-infrastructure"
    intensity: 5
    notes: "Crisis visualization - transformer explosion"

arc_visualization:
  type: "5-part"
  peaks: [7, 12]
  nadir: null
  concession: null
```

---

## Task 4: Content Allocation

### Purpose
Assign specific source content to each slide.

### Input
```yaml
slide_sequence: (from Task 3)
source_analysis: (from Task 2)
compression_ratio: float
```

### Output
```yaml
allocations:
  - slide_number: int
    headline:
      text: string
      source: "direct" | "synthesized" | "dramatized"
      source_paragraph: int | null
    body_text:
      summary: string
      source_paragraphs: [int]
      compression_applied: float
    quote:
      text: string | null
      source_paragraph: int | null
    key_metaphor: string | null
```

### Example Output

```yaml
allocations:
  - slide_number: 3
    headline:
      text: "The Financial Sleight of Hand"
      source: "synthesized"
      source_paragraph: null
    body_text:
      summary: "We try to fix shortages by writing checks—a flow of political will that offers the comfort of immediate action. But this is a mechanical cruelty..."
      source_paragraphs: [2]
      compression_applied: 1.8
    quote:
      text: "The ink on the check dries in seconds; the concrete in a foundation takes a season."
      source_paragraph: 2
    key_metaphor: "check vs. concrete"
```

---

## Task 5: Visual Design Specification

### Purpose
Establish visual rules for the presentation based on genre.

### Input
```yaml
genre: string
content_allocation: (from Task 4)
metaphor_inventory: (from Task 2)
```

### Output
```yaml
design_system:
  background:
    color: string (hex)
    texture: string

  typography:
    headline:
      family: "serif" | "sans-serif" | "monospace"
      weight: string
      style: "title_case" | "all_caps" | "mixed"
    body:
      family: string
      size: string
    quote:
      family: string
      style: "italic" | "bold" | "regular"

  color_palette:
    primary_accent: string (hex)
    secondary_accent: string (hex)
    symbolism:
      - color: string (hex)
        meaning: string

  motif:
    type: "unified" | "distributed"
    primary_visual: string
    persistence: float (0-1, how many slides)

  layout_preferences:
    diagram_heavy: boolean
    comparison_percentage: float
    preferred_patterns: [string]
```

### Example Output

```yaml
design_system:
  background:
    color: "#F0EDE8"
    texture: "warm grey with technical grid"

  typography:
    headline:
      family: "serif"
      weight: "bold"
      style: "mixed"
    body:
      family: "serif"
      size: "13pt"
    quote:
      family: "serif"
      style: "italic"

  color_palette:
    primary_accent: "#0077B6"
    secondary_accent: "#E85D04"
    symbolism:
      - color: "#0077B6"
        meaning: "flow, abundance, positive"
      - color: "#E85D04"
        meaning: "stagnation, warning, problem"

  motif:
    type: "extended"
    primary_visual: "water infrastructure (cistern, valve, pipe)"
    persistence: 0.67

  layout_preferences:
    diagram_heavy: true
    comparison_percentage: 0.20
    preferred_patterns: ["split_vertical", "infographic", "text_plus_image"]
```

---

## Task 6: Slide Specification

### Purpose
Generate complete, executable specifications for each slide.

### Input
```yaml
content_allocation: (from Task 4)
design_system: (from Task 5)
slide_sequence: (from Task 3)
```

### Output
```yaml
slides:
  - number: int
    role: string

    content:
      headline: string
      subheadline: string | null
      body_text: string | null
      quote: string | null
      labels: [string] | null

    layout:
      pattern: string
      grid_description: string

    visual:
      image_spec:
        subject: string
        mood: string
        color_temperature: string
        metaphor_visualized: string
      color_usage:
        background: string (hex)
        accents_used: [string (hex)]
      typography_notes: string

    arc_position:
      intensity: 1-5
      function: string
      transition_to_next: string
```

### Example Output (Single Slide)

```yaml
slides:
  - number: 4
    role: "evidence"

    content:
      headline: "The Cistern"
      subheadline: null
      body_text: |
        In the language of systems, our collective capacity to live is our Stock.
        For years, the inflows—the crews, the brick, the mortar—have been slowed to a trickle.
        We are subsidizing the demand for a life we refuse to actually build.
      quote: null
      labels:
        - "INFLOWS (Construction)"
        - "SUBSIDIES (Cash)"
        - "STOCK (Housing/Power/Capacity)"

    layout:
      pattern: "infographic"
      grid_description: "Technical diagram left/center (65%), text column right (35%)"

    visual:
      image_spec:
        subject: "Industrial water cistern with labeled inputs - pipe from left (trickling), bucket pouring from top (overflowing), tank in center"
        mood: "Diagnostic, systemic, explanatory"
        color_temperature: "Industrial greys and rust; blue water; orange warnings"
        metaphor_visualized: "Economic capacity as water tank; subsidies missing the tank"
      color_usage:
        background: "#F0EDE8"
        accents_used: ["#0077B6", "#E85D04"]
      typography_notes: "Technical diagram labels in sans-serif small-caps"

    arc_position:
      intensity: 4
      function: "Core explanatory diagram - establishes systems vocabulary"
      transition_to_next: "From understanding the system to identifying who blocks it"
```

---

## Task 7: Image Prompt Generation

### Purpose
Transform slide specifications into Gemini-compatible image prompts using the Nano-Banana Pro methodology.

### Input
```yaml
slide_spec: (single slide from Task 6)
design_system: (from Task 5)
presentation_context:
  genre: string
  title: string
  slide_number: int
  total_slides: int
```

### Output
```yaml
image_prompt:
  full_prompt: string  # Complete Gemini-ready prompt
  sections:
    goal: string
    subject: string
    composition: string
    setting: string
    lighting: string
    text_elements: string | null
    style: string
    fidelity: string
    consistency: string
  generation_notes:
    aspect_ratio: string
    negative_prompts: [string] | null
    key_requirements: [string]
```

### Nano-Banana Pro Sections

The methodology structures prompts in 9 sections:

1. **Goal/Context** - Why the image exists
2. **Subject** - Precise description
3. **Composition & Layout** - Camera angle, framing
4. **Setting & Environment** - Location, era, mood
5. **Lighting & Atmosphere** - Soft/hard, warm/cold
6. **Text Elements** - Any text to include (in quotes)
7. **Style** - Photorealistic, editorial, etc.
8. **Fidelity** - Texture detail, resolution
9. **Consistency Notes** - Identity locking for series

### Transformation Mapping

| Task 6 Field | Maps To |
|--------------|---------|
| `image_spec.subject` | Subject + Setting |
| `image_spec.mood` | Setting + Lighting |
| `image_spec.color_temperature` | Lighting |
| `image_spec.metaphor_visualized` | Goal + Subject |
| `image_spec.style_notes` | Style + Fidelity |
| `layout.pattern` | Composition |
| `content.labels` | Text elements |

### Genre-Specific Patterns

**Personal Essay:**
- Varied styles per slide
- No strict consistency locking
- Emotional lighting cues

**Analytical Critique:**
- Unified visual metaphor
- Strict color symbolism
- Identity lock on dichotomy visual

**Policy Argument:**
- Extended metaphor components
- Infrastructure/documentary aesthetic
- Identity lock on infrastructure elements

### Example Output (abbreviated)

```yaml
image_prompt:
  full_prompt: |
    GOAL: Technical diagram for policy presentation explaining economic capacity...
    SUBJECT: Industrial water cistern cutaway diagram showing three key elements...
    COMPOSITION: Straight-on technical diagram view. Tank centered...
    SETTING: Abstract industrial space. Technical grid lines...
    LIGHTING: Even, flat lighting as in technical illustrations...
    STYLE: Technical illustration with industrial realism...
    FIDELITY: High detail on mechanical components...
    CONSISTENCY: Extended water infrastructure metaphor. Colors: #0077B6, #E85D04...
  sections:
    goal: "Technical diagram for policy presentation..."
    subject: "Industrial water cistern cutaway..."
    # ... remaining sections
  generation_notes:
    aspect_ratio: "16:9"
    negative_prompts: ["photorealistic photograph", "cartoon style"]
    key_requirements: ["Water must clearly MISS the tank"]
```

---

## Task Dependencies

```
Task 1 ──────────────────────────────────────────────┐
   │                                                 │
   ▼                                                 │
Task 2 ──────────────────────────────────┐           │
   │                                     │           │
   ▼                                     │           │
Task 3 ◄────────────────────────────────┘           │
   │                                                 │
   ▼                                                 │
Task 4 ◄────────────────────────────────────────────┤
   │                                                 │
   ▼                                                 │
Task 5 ◄────────────────────────────────────────────┘
   │
   ▼
Task 6
   │
   ▼
Task 7 ◄──────────────── Task 5 (design system for consistency)
   │
   ▼
[Image Prompts] ────────▶ Gemini ────────▶ [Images]
```

**Sequential Dependencies**:
- Task 2 requires Task 1 output (genre)
- Task 3 requires Task 2 output (analysis)
- Task 4 requires Task 2 + Task 3 outputs
- Task 5 requires Task 1 + Task 4 outputs
- Task 6 requires all previous outputs
- Task 7 requires Task 6 output (slide specs) + Task 5 output (design system)

**Parallelization Potential**:
- Tasks 4 and 5 could potentially run in parallel after Task 3 completes
- However, Task 5 benefits from seeing content allocation (Task 4) for motif decisions
- Task 7 can process slides in parallel (each slide's prompt is independent)

---

## Implementation Notes

### Prompt Design Considerations

1. **Task 1 (Genre Classification)**
   - Provide clear genre definitions with examples
   - Include signal detection checklist
   - Request confidence score with reasoning

2. **Task 2 (Source Analysis)**
   - Structured output format critical
   - Quotable passage quality checklist
   - Metaphor inventory should note visualizability

3. **Task 3 (Structure Planning)**
   - Genre-specific arc templates as reference
   - Role vocabulary standardization important
   - Intensity ratings enable arc visualization

4. **Task 4 (Content Allocation)**
   - Compression ratio enforcement
   - Track source provenance for verification
   - Flag when synthesis/invention is used

5. **Task 5 (Visual Design)**
   - Genre-specific design rules as lookup
   - Color symbolism consistency check
   - Motif persistence target

6. **Task 6 (Slide Specification)**
   - Executable detail level
   - Image prompts must be specific enough for generation
   - Layout patterns from standard library

7. **Task 7 (Image Prompt Generation)**
   - Follow Nano-Banana Pro 9-section structure
   - Genre-specific consistency rules
   - Layout pattern → composition mapping
   - Intensity → lighting/contrast mapping
   - Include negative prompts to prevent common failures

### Error Handling

- If genre classification is uncertain (confidence < 0.6), request human review
- If quotable passages insufficient, note gaps in Task 2 output
- If compression ratio cannot be achieved, flag for review
- If metaphor inventory empty, default to distributed metaphor strategy

### Validation Checkpoints

After each task, verify:
1. Output format matches schema
2. Required fields populated
3. Genre-specific rules applied correctly
4. Cross-references to source are accurate
5. (Task 7) Full prompt is coherent and can be used directly with Gemini
6. (Task 7) Consistency notes maintain visual identity across slides
