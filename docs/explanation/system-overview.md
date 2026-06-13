# System Architecture: Essay-to-Slides Generation

## Overview

This document describes the conceptual architecture for transforming essays into visual presentations, reverse-engineered from three NotebookLM-generated examples.

**Key Insight**: The system is **genre-aware** - it detects source content type and adapts structure, visual language, and extraction patterns accordingly.

---

## 1. Bird's Eye View

### High-Level Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                            ESSAY-TO-SLIDES PIPELINE                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌──────────┐   ┌─────────────┐   ┌─────────────┐   ┌──────┐   ┌───────┐   ┌──────┐│
│  │  SOURCE  │──▶│  ANALYSIS   │──▶│  SYNTHESIS  │──▶│SLIDES│──▶│ IMAGE │──▶│GEMINI││
│  │  ESSAY   │   │   PHASE     │   │   PHASE     │   │ SPEC │   │PROMPTS│   │      ││
│  └──────────┘   └──────┬──────┘   └──────┬──────┘   └──────┘   └───────┘   └──────┘│
│                        │                 │                                          │
│                        ▼                 ▼                                          │
│                ┌───────────────┐ ┌───────────────┐                                  │
│                │    Genre      │ │    Design     │                                  │
│                │ Classification│ │   Decisions   │                                  │
│                └───────────────┘ └───────────────┘                                  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Conceptual Data Flow

```
┌─────────────┐
│ Source.md   │
│ (essay)     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│                  ANALYSIS PHASE                      │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐       │
│  │  Genre    │  │ Structure │  │ Quotables │       │
│  │  Detect   │  │  Parse    │  │  Extract  │       │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘       │
│        │              │              │              │
│        └──────────────┼──────────────┘              │
│                       ▼                             │
│              ┌─────────────────┐                    │
│              │ Source Analysis │                    │
│              │    Document     │                    │
│              └────────┬────────┘                    │
└───────────────────────┼─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                 SYNTHESIS PHASE                      │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐       │
│  │ Narrative │  │  Visual   │  │   Slide   │       │
│  │ Structure │  │  Design   │  │   Specs   │       │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘       │
│        │              │              │              │
│        └──────────────┼──────────────┘              │
│                       ▼                             │
│              ┌─────────────────┐                    │
│              │  Presentation   │                    │
│              │  Specification  │                    │
│              └────────┬────────┘                    │
└───────────────────────┼─────────────────────────────┘
                        │
                        ▼
                ┌───────────────┐
                │ Per-Slide     │
                │ Specifications│
                │ (text, layout,│
                │  image spec)  │
                └───────┬───────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│                IMAGE GENERATION PHASE               │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐       │
│  │  Nano-    │  │  Genre    │  │Consistency│       │
│  │  Banana   │  │  Style    │  │  Locking  │       │
│  │  Pro      │  │  Rules    │  │           │       │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘       │
│        │              │              │              │
│        └──────────────┼──────────────┘              │
│                       ▼                             │
│              ┌─────────────────┐                    │
│              │  Provider-Ready │                    │
│              │  Image Prompts  │                    │
│              └────────┬────────┘                    │
└───────────────────────┼─────────────────────────────┘
                        │
                        ▼
                ┌───────────────┐
                │ IMAGE PROVIDER│
                │ Gemini/OpenAI │
                │ /xAI          │
                └───────┬───────┘
                        │
                        ▼
                ┌───────────────┐
                │   Generated   │
                │    Images     │
                └───────────────┘
```

---

## 2. Analysis Phase

The analysis phase examines the source essay to understand its nature and extract raw materials.

### 2.1 Genre Classification

**Purpose**: Determine the content type to select appropriate downstream parameters.

**Detected Genres**:

| Genre | Indicators | Example |
|-------|------------|---------|
| Personal Essay | First-person, sensory language, emotional reflection | Cellophane World |
| Analytical Critique | Third-person, technical terms, systematic argument | Map and River |
| Policy Argument | Systems vocabulary, problem-solution structure, human stakes | Mechanics of Plenty |
| Fiction | Characters, dialogue, scene descriptions, narrative events | — |
| Strategic Diagnostic | Diagnostic framing, strategic analysis, recommendations | — |
| Conceptual Essay | Definition- and distinction-driven philosophical argument | — |

**Classification Signals**:
- Voice (first-person reflection vs. analytical distance)
- Vocabulary (sensory vs. technical vs. systems)
- Structure (narrative arc vs. logical argument vs. diagnostic)
- Emotional register (personal stakes vs. intellectual challenge)

### 2.2 Structural Analysis

**Purpose**: Parse the essay into workable units.

**Extracted Elements**:
- Section headers (if present)
- Paragraph boundaries
- Logical segments (intro, body sections, conclusion)
- Transition points
- Climactic moments

### 2.3 Quotable Passage Extraction

**Purpose**: Identify text suitable for slide presentation.

**Selection Criteria** (confirmed across all three presentations):
1. **Standalone clarity** - Makes sense without surrounding context
2. **Aphoristic structure** - Memorable, quotable form
3. **Visualizability** - Suggests imagery
4. **Rhythmic quality** - Sounds good when read
5. **Emotional/intellectual punch** - Creates impact

### 2.4 Metaphor Inventory

**Purpose**: Catalog visual opportunities.

**Extraction Process**:
- Identify explicit metaphors in text
- Note recurring imagery patterns
- Assess metaphor dominance (single controlling vs. distributed)
- Map abstract concepts to potential visuals

### 2.5 Emotional Arc Mapping

**Purpose**: Understand the source's dramatic structure.

**Analysis Points**:
- Opening energy level
- Rising/falling tension
- Peak moments (emotional or intellectual)
- Resolution trajectory
- Potential nadir points

---

## 3. Synthesis Phase

The synthesis phase generates the presentation structure and specifications.

### 3.1 Narrative Structure Selection

**Purpose**: Choose the arc shape based on genre.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NARRATIVE STRUCTURE BY GENRE                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  PERSONAL ESSAY (3-Act Emotional)                                   │
│  ────────────────────────────────                                   │
│       ╱╲                                                            │
│      ╱  ╲    ╱╲                                                     │
│     ╱    ╲  ╱  ╲                                                    │
│    ╱      ╲╱    ╲                                                   │
│   Hook → Build → Nadir → Climax → Resolution                        │
│                                                                      │
│  ANALYTICAL CRITIQUE (4-Part Argument)                              │
│  ─────────────────────────────────────                              │
│            ┌────────────┐                                           │
│           ╱              ╲                                          │
│          ╱                ╲   ╱╲                                    │
│         ╱                  ╲ ╱  ╲                                   │
│   Frame → Critique(sustained) → Concede → Reframe                   │
│                                                                      │
│  POLICY ARGUMENT (5-Part Policy)                                    │
│  ───────────────────────────────                                    │
│        ╱╲          ╱╲                                               │
│       ╱  ╲        ╱  ╲                                              │
│      ╱    ╲      ╱    ╲                                             │
│     ╱      ╲    ╱      ╲                                            │
│   Ground → Diagnose → Reframe → Apply(crisis) → Resolve             │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Slide Planning

**Purpose**: Determine slide count and role assignment.

**Slide Roles** (universal vocabulary):

| Role | Function | Typical Position |
|------|----------|------------------|
| Title | Establish topic, create intrigue | First |
| Hook | Draw reader in emotionally | Early |
| Build | Develop argument/narrative | Early-middle |
| Peak/Climax | Maximum intensity | Middle or late |
| Nadir | Lowest point (if applicable) | Before climax |
| Concession | Acknowledge counterpoint | Late-middle |
| Reframe | Shift perspective | Middle or late |
| Resolution | Provide closure | Final |

**Slide Count Heuristics**:
- ~1 slide per major concept/section
- Split dense sections into multiple slides
- Target 14-16 slides total
- Allow breathing room (not every slide is high-intensity)

### 3.3 Content Allocation

**Purpose**: Assign source content to slides.

**Allocation Rules**:
- Lead with strongest quotes
- One core idea per slide
- Preserve key phrases verbatim
- Compress supporting material
- Invent headers where source lacks them

**Compression Ratios by Genre**:

| Genre | Ratio | Reasoning |
|-------|-------|-----------|
| Personal Essay | 4:1 | Feeling carries beyond words |
| Analytical Critique | 2:1 | Precision matters |
| Policy Argument | 1.7:1 | Source already visual/quote-rich |

### 3.4 Visual Design System Selection

**Purpose**: Establish visual rules for consistency.

**Design Decisions by Genre**:

| Aspect | Personal | Analytical | Policy |
|--------|----------|------------|--------|
| Headline Font | Serif (elegant) | Monospace | Serif (authoritative) |
| Color System | Varied per-slide | Strict dichotomy | Dual accent |
| Motif Persistence | Low | High | Medium-high |
| Diagram Usage | Low | Medium | High |

### 3.5 Image Specification

**Purpose**: Define visual requirements per slide.

**Image Spec Components**:
- Subject description
- Mood/emotional tone
- Color temperature
- Metaphor being visualized
- Layout integration notes

### 3.6 Layout Assignment

**Purpose**: Select layout pattern per slide.

### 3.7 Image Prompt Generation

**Purpose**: Transform slide image specs into Gemini-compatible prompts.

**Methodology**: Nano-Banana Pro 9-section structure:
1. Goal/Context - Why the image exists
2. Subject - Precise description
3. Composition & Layout - Camera angle, framing
4. Setting & Environment - Location, era, mood
5. Lighting & Atmosphere - Soft/hard, warm/cold
6. Text Elements - Any text to include
7. Style - Photorealistic, editorial, etc.
8. Fidelity - Texture detail, resolution
9. Consistency Notes - Identity locking for series

**Genre-Specific Prompt Patterns**:

| Genre | Style Emphasis | Consistency Approach |
|-------|---------------|---------------------|
| Personal Essay | Varied, emotional, organic | Tonal consistency only |
| Analytical Critique | Unified, technical, precise | Strict identity locking on dichotomy visual |
| Policy Argument | Documentary, infrastructure | Identity locking on extended metaphor elements |

**Layout Pattern Library**:

```
PATTERN 1: Split Horizontal (60/40)
┌────────────────────────────┐
│       IMAGE (60%)          │
├────────────────────────────┤
│  HEADLINE  │  BODY TEXT    │
└────────────────────────────┘

PATTERN 2: Split Vertical (45/55)
┌─────────────┬──────────────┐
│             │  HEADLINE    │
│   IMAGE     │  Body text   │
│             │  Quote       │
└─────────────┴──────────────┘

PATTERN 3: Comparison (50/50)
┌─────────────┬──────────────┐
│  HEADER A   │  HEADER B    │
│  [Image]    │  [Image]     │
│  Caption    │  Caption     │
├─────────────┴──────────────┤
│      VERDICT/QUOTE         │
└────────────────────────────┘

PATTERN 4: Full-Bleed with Overlay
┌────────────────────────────┐
│  ┌──────────────┐          │
│  │ QUOTE TEXT   │          │
│  │ (on image)   │          │
│  └──────────────┘          │
│                  ┌─────────┤
│                  │ CALLOUT │
└──────────────────┴─────────┘

PATTERN 5: Infographic/Diagram
┌────────────────────────────┐
│         [Diagram]          │
│    Label ──┘  └── Label    │
├────────────────────────────┤
│     "Quote/Explanation"    │
└────────────────────────────┘

PATTERN 6: Typography-Focused
┌────────────────────────────┐
│  background words words    │
│    ╔═══════════════╗       │
│    ║  BIG TEXT     ║       │
│    ╚═══════════════╝       │
├────────────────────────────┤
│      Body explanation      │
└────────────────────────────┘
```

---

## 4. Decision Points

### 4.1 Compression Decision

```
                    ┌─────────────────┐
                    │  Source Essay   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Genre Detection │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Personal   │  │  Analytical  │  │    Policy    │
    │    Essay     │  │   Critique   │  │   Argument   │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  Ratio: 4:1  │  │  Ratio: 2:1  │  │ Ratio: 1.7:1 │
    │   Compress   │  │   Preserve   │  │    Minimal   │
    │  aggressively│  │   precision  │  │  compression │
    └──────────────┘  └──────────────┘  └──────────────┘
```

### 4.2 Metaphor Strategy Decision

```
                    ┌─────────────────┐
                    │  Source Essay   │
                    └────────┬────────┘
                             │
                             ▼
              ┌──────────────────────────┐
              │ Dominant Metaphor Found? │
              └────────────┬─────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
       ┌─────────────┐          ┌─────────────┐
       │     YES     │          │     NO      │
       └──────┬──────┘          └──────┬──────┘
              │                        │
              ▼                        ▼
       ┌─────────────────┐      ┌─────────────────┐
       │ Unified motif   │      │ Distributed     │
       │ (persist across │      │ metaphors       │
       │  most slides)   │      │ (vary per slide)│
       └─────────────────┘      └─────────────────┘
              │                        │
              ▼                        ▼
       Map/River style          Cellophane style
       Mechanics style
```

### 4.3 Color System Decision

```
                    ┌─────────────────┐
                    │     Genre       │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Personal   │  │  Analytical  │  │    Policy    │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │    VARIED    │  │    STRICT    │  │  DUAL ACCENT │
    │  Per-slide   │  │  Dichotomy   │  │  Problem/    │
    │  emotional   │  │  (A vs B)    │  │  Solution    │
    │  matching    │  │  throughout  │  │  colors      │
    └──────────────┘  └──────────────┘  └──────────────┘
```

### 4.4 Closing Strategy Decision

```
                    ┌─────────────────┐
                    │     Genre       │
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Personal   │  │  Analytical  │  │    Policy    │
    └──────┬───────┘  └──────┬───────┘  └──────┬───────┘
           │                 │                 │
           ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │   Personal   │  │   General    │  │   Human      │
    │   Action     │  │  Imperative  │  │   Return     │
    │              │  │              │  │   + Hope     │
    │ "I'm hitting │  │ "LOOK BEYOND │  │ "The air     │
    │  backspace"  │  │  THE LIST"   │  │  is moving"  │
    └──────────────┘  └──────────────┘  └──────────────┘
```

---

## 5. Pattern Library

### 5.1 Common Patterns (Genre-Independent)

These rules apply to ALL presentations regardless of content type:

**Visual Foundation**:
- Background: Cream/warm grey (#E8E0D5 to #F0EDE8)
- Body text: Serif font, regular weight, 12-14pt
- Footer: Optional branding bottom-right, small and unobtrusive

**Content Rules**:
- Opening must hook (question, paradox, or human stakes)
- Closing must resolve (action, imperative, or hope)
- Quotes must be standalone and visualizable
- One core idea per slide maximum
- Headers can be invented if source lacks them

**Visual Rules**:
- Visual motif should reflect central metaphor
- Maintain consistent typography hierarchy
- Use white space generously
- Frame images with technical drawing aesthetic (optional)

### 5.2 Genre-Specific Patterns

#### Personal Essay Rules

| Aspect | Pattern |
|--------|---------|
| Structure | 3-act emotional arc |
| Compression | 4:1 (aggressive) |
| Metaphors | Distributed, sensory, embodied |
| Colors | Varied per-slide emotional matching |
| Headlines | Serif, elegant, title case |
| Imagery | Rain, jungle, soil, organic materials |
| Closing | Personal action by narrator |
| Nadir | Required before climax |
| Human element | Throughout |

#### Analytical Critique Rules

| Aspect | Pattern |
|--------|---------|
| Structure | 4-part argument (Frame → Critique → Concede → Reframe) |
| Compression | 2:1 (preserve precision) |
| Metaphors | Unified dichotomy (A vs. B) throughout |
| Colors | Strict symbolism (one color per concept) |
| Headlines | Monospace, all-caps, technical |
| Imagery | Diagrams, charts, conceptual illustrations |
| Closing | General imperative/call-to-action |
| Concession | Required for credibility |
| Human element | Minimal |

#### Policy Argument Rules

| Aspect | Pattern |
|--------|---------|
| Structure | 5-part policy (Ground → Diagnose → Reframe → Apply → Resolve) |
| Compression | 1.7:1 (minimal) |
| Metaphors | Extended system (multiple components) |
| Colors | Dual accent (problem vs. solution) |
| Headlines | Serif, authoritative, mixed case |
| Imagery | Infrastructure, industrial, documentary |
| Closing | Return to human stakes + hope |
| Peaks | Two allowed (diagnosis + crisis) |
| Human element | Bookending (open and close) |

---

## 6. Output Specifications

The system produces two levels of output:

### 6.1 Slide Specifications (Task 6 Output)

Per-slide specifications containing text, layout, and visual requirements:

```yaml
slide_01:
  role: "title"
  headline: "The Mechanics of Plenty"
  subheadline: "Navigating the Abundance Agenda..."
  body_text: null
  quote: null
  layout: "magazine_title"
  image_spec:
    subject: "Dam with water releasing through spillways"
    mood: "Powerful, promising"
    color_temp: "Cool industrial"
    metaphor: "Abundance unleashed"
  design_notes:
    - "Issue badge top-right"
    - "Hero image dominates"
```

### 6.2 Image Prompts (Task 7 Output)

Gemini-compatible prompts following the Nano-Banana Pro methodology:

```yaml
image_prompt:
  full_prompt: |
    GOAL: Title slide visual for policy presentation about economic abundance...
    SUBJECT: Massive concrete dam at golden hour, water cascading through spillways...
    COMPOSITION: Wide shot, dam centered, human silhouettes for scale...
    SETTING: Industrial infrastructure, sunset, monumental scale...
    LIGHTING: Golden hour warmth on grey concrete, dramatic sky...
    STYLE: Documentary photography, architectural emphasis...
    FIDELITY: High detail on concrete texture, water motion blur...
    CONSISTENCY: Extended infrastructure metaphor, blue #0077B6 for flow...
  sections:
    goal: "Title slide visual establishing infrastructure theme"
    subject: "Massive concrete dam with water releasing"
    composition: "Wide shot, dam centered, silhouettes for scale"
    setting: "Industrial, sunset, monumental"
    lighting: "Golden hour on grey concrete"
    text_elements: null
    style: "Documentary photography"
    fidelity: "High detail, slight desaturation except sky"
    consistency: "Infrastructure metaphor, blue for abundance"
  generation_notes:
    aspect_ratio: "16:9"
    negative_prompts: ["cartoon", "illustration"]
    key_requirements: ["Human scale reference", "Water in motion"]
```

### 6.3 Downstream Uses

These specifications can be used to:
1. Generate images via any supported provider (Gemini, OpenAI gpt-image-2, xAI Grok)
2. Create slides in presentation software (using Task 6 specs)
3. Guide human designers in production
4. Validate generated images against requirements

For the per-task breakdown of the slide pipeline, see [Task Decomposition](task-decomposition.md). For the infographic pipeline, see [Pipeline Architectures](pipeline-architectures.md).
