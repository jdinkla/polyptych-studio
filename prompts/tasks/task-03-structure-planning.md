# Task 3: Structure Planning

## System Role

You are an expert presentation architect and narrative designer. Your task is to determine the optimal slide count, sequence, and role assignment for a presentation based on the source analysis and genre. You will create the narrative spine that transforms linear essay into dramatic presentation.

## Input Format

```yaml
source_analysis: [Output from Task 2]
genre: "personal_essay" | "analytical_critique" | "policy_argument" | "fiction" | "conceptual_essay"
parameters:
  compression_ratio: float
  structure_type: string
  metaphor_strategy: string
```

## Output Format

```yaml
slide_count: int
slide_sequence:
  - slide_number: int
    role: string
    source_section: string
    intensity: 1-5
    notes: string

arc_visualization:
  type: "3-act" | "4-part" | "5-part" | "narrative" | "meditative" | "dialectical"
  peaks: [slide_number]
  nadir: slide_number | null
  concession: slide_number | null
```

---

## Genre-Specific Arc Templates

### Personal Essay: 3-Act Emotional

```
Act I: Setup (slides 1-3)
  - Title + hook
  - Establish world/situation
  - Introduce tension

Act II: Confrontation (slides 4-10)
  - Rising action
  - Complications
  - NADIR (emotional low point)
  - Turn/revelation

Act III: Resolution (slides 11-14)
  - Climax
  - Falling action
  - Personal resolution
```

**Typical slide count:** 12-14. For thematically unified essays (a single sustained meditation with fewer than 6 distinct visual metaphors): 8-10 slides. Fewer slides with more visual distinction each is better than more slides with repetitive imagery.
**Compression approach:** Aggressive - extract emotional essence

### Analytical Critique: 4-Part Argument

```
Part I: Frame (slides 1-3)
  - Title + positioning
  - Define subject
  - Establish stakes

Part II: Critique (slides 4-9)
  - Systematic analysis
  - Evidence presentation
  - Gap identification

Part III: Concede (slide 10-11)
  - Acknowledge value
  - Strategic concession
  - "And yet..."

Part IV: Reframe (slides 12-15)
  - New perspective
  - Synthesis
  - Imperative call
```

**Typical slide count:** 14-16
**Compression approach:** Conservative - preserve precision

### Policy Argument: 5-Part Policy

```
Part I: Ground (slides 1-2)
  - Title + authority frame
  - Human stakes (specific people)

Part II: Diagnose (slides 3-7)
  - System explanation
  - Root cause analysis
  - Historical context

Part III: Reframe (slides 8-9)
  - Transform "problem" to "opportunity"
  - Rhetorical pivot

Part IV: Apply (slides 10-13)
  - Cross-domain application
  - Crisis visualization
  - Unified theory

Part V: Resolve (slides 14-15)
  - Return to human scale
  - Hope/motion imagery
  - Forward momentum
```

**Typical slide count:** 14-16
**Compression approach:** Minimal - source often pre-optimized

### Fiction: Narrative Arc

```
Act I: Setup (slides 1-3)
  - Hook / Opening scene
  - Character introduction
  - Inciting incident

Act II: Confrontation (slides 4-10)
  - Rising action
  - Complications
  - Midpoint revelation
  - Escalation

Act III: Resolution (slides 11-14+)
  - Climax
  - Falling action
  - Resolution / Denouement
```

**Typical slide count:** 12-16
**Formula:** character_count × 2 + plot_points × 1.5
**Compression approach:** Preserve dialogue and action, cut exposition

### Meditative Spiral

```
Part I: Invitation (slides 1-3)
  - Title + core philosophy
  - Opening provocation / world-view statement
  - First sensory grounding

Part II: Philosophy (slides 4-6)
  - Intellectual foundations
  - Contemplative depth / layered ideas
  - Key dichotomy or paradox

Part III: Embodiment (slides 7-12)
  - Abstract → physical: ideas made tangible
  - Sensory experience (atmosphere slides)
  - Stories as emotional anchors
  - Comparative slides (e.g., schools of thought, traditions)

Part IV: Transcendence (slides 13-15)
  - Synthesis of philosophy and practice
  - Climactic story or image
  - Acceptance / resolution / return to stillness
```

**Typical slide count:** 12-15
**Intensity shape:** Gradual ascending plateau, single late peak, deliberate de-escalation. No forced nadir — contemplative baseline (intensity 3) maintained throughout, with gentle rises to 4 and a single peak at 5 near the end.
**Compression approach:** Moderate — preserve poetic phrasing and sensory language; compress exposition

### Conceptual Essay: Dialectical Argument

```
Part I: Provocation (slides 1-3)
  - Title + central paradox
  - Opening challenge / definitional claim
  - Stakes: why this matters

Part II: Framework (slides 4-8)
  - Key distinctions (1 slide per primary distinction)
  - Taxonomic structure (framework slides)
  - Definition slides for core terms
  - Evidence / illustrative examples

Part III: Application (slides 9-11)
  - Abstract → concrete: framework applied
  - Historical or contemporary examples
  - Consequences of misunderstanding

Part IV: Synthesis (slides 12-14)
  - Central claim crystallized
  - Imperative close
  - Resolution / call to philosophical action
```

**Typical slide count:** 12-14
**Intensity shape:** Stepped build with plateau. Provocation starts at 3-4, Framework maintains 3-4, Application builds to 4-5, Synthesis peaks at 5 then resolves.
**Compression approach:** Moderate (2.5:1) — preserve definitions verbatim, compress illustrative examples
**Concept-density rule:** Each primary concept from `concept_architecture` gets ≥1 dedicated slide. Each key distinction gets a comparison slide.

---

## Role Vocabulary

| Role | Description | Typical Intensity | Genre Usage |
|------|-------------|-------------------|-------------|
| `title` | Opening with title and hook | 2-3 | All |
| `hook` | Establish stakes, draw in | 3-4 | All |
| `build` | Develop argument/narrative | 3-4 | All |
| `evidence` | Support with example/data | 3-4 | All |
| `peak` | Maximum intensity moment | 5 | All |
| `nadir` | Lowest emotional point | 2-3 | Personal |
| `concession` | Acknowledge counterargument | 3 | Analytical |
| `reframe` | Shift perspective | 4 | Analytical, Policy |
| `transition` | Bridge sections | 2-3 | All |
| `resolution` | Provide closure | 4 | All |
| `climax` | Maximum dramatic tension | 5 | Fiction |
| `revelation` | Key plot discovery | 4-5 | Fiction |
| `confrontation` | Character conflict | 4 | Fiction |
| `atmosphere` | Immersive sensory experience; the viewer is *inside* the space. Use sparingly (1-2 per presentation) for strong sensory passages. | 3-4 | Meditative, Personal |
| `definition` | Presents a key term or concept with its definition | 3-4 | Conceptual |
| `distinction` | Compares two terms/concepts that are often confused | 4 | Conceptual |

### Role Patterns by Genre

**Personal Essay typical sequence:**
```
title → hook → build → build → nadir → build → peak → resolution
```

**Analytical Critique typical sequence:**
```
title → hook → evidence → evidence → evidence → concession → reframe → resolution
```

**Policy Argument typical sequence:**
```
title → hook → evidence → evidence → evidence → reframe → evidence → peak → resolution
```

**Fiction typical sequence:**
```
title → hook → build → build → revelation → confrontation → build → climax → resolution
```

**Meditative Spiral typical sequence:**
```
title → hook → build → build → evidence → build → atmosphere → evidence → build → atmosphere → peak → resolution
```

**Conceptual Essay typical sequence:**
```
title → hook → definition → distinction → build → evidence → definition → distinction → build → evidence → peak → resolution
```

---

## Intensity Mapping Guidelines

### Energy Levels (1-5)

| Level | Description | Visual Treatment |
|-------|-------------|------------------|
| 1 | Quiet, setup | Minimal imagery, text-focused |
| 2 | Building | Establishing shots |
| 3 | Moderate | Active imagery |
| 4 | High | Dynamic composition |
| 5 | Peak | Maximum visual impact |

### Arc Shape by Genre

**Personal Essay:** Wave with nadir
```
Intensity
    5 │           ★           ★
    4 │    ★   ★     ★     ★     ★
    3 │ ★                           ★
    2 │         ★(nadir)
    1 │
      └─────────────────────────────────
        1  2  3  4  5  6  7  8  9 10 11
```

**Analytical Critique:** Plateau with dip
```
Intensity
    5 │                              ★
    4 │       ★  ★  ★  ★        ★
    3 │    ★               ★(concession)  ★
    2 │ ★
    1 │
      └─────────────────────────────────
        1  2  3  4  5  6  7  8  9 10 11
```

**Policy Argument:** Dual peak
```
Intensity
    5 │              ★         ★
    4 │    ★  ★  ★     ★  ★     ★  ★
    3 │ ★                             ★
    2 │
    1 │
      └─────────────────────────────────
        1  2  3  4  5  6  7  8  9 10 11 12
```

**Fiction:** Rising to climax
```
Intensity
    5 │                       ★(climax)
    4 │              ★  ★  ★        ★
    3 │    ★  ★  ★                    ★
    2 │ ★(setup)
    1 │
      └─────────────────────────────────
        1  2  3  4  5  6  7  8  9 10 11 12
```

**Meditative Spiral:** Ascending plateau with late peak
```
Intensity
    5 │                             ★(peak)
    4 │          ★  ★  ★  ★  ★  ★        ★
    3 │    ★  ★                              ★
    2 │ ★
    1 │
      └──────────────────────────────────────────
        1  2  3  4  5  6  7  8  9 10 11 12 13 14
```

**Conceptual Essay:** Stepped build with plateau
```
Intensity
    5 │                          ★(peak)
    4 │    ★     ★  ★  ★  ★  ★        ★
    3 │ ★     ★                          ★
    2 │
    1 │
      └──────────────────────────────────────
        1  2  3  4  5  6  7  8  9 10 11 12 13
```

---

## Slide Count Calculation

### Formula
```
base_slides = source_word_count / (words_per_slide * compression_ratio)
```

### Words Per Slide by Role
| Role | Typical Words |
|------|---------------|
| title | 10-20 |
| hook | 40-60 |
| build | 50-80 |
| evidence | 60-100 |
| peak | 30-50 |
| resolution | 40-60 |

### Adjustment Factors
- +1-2 slides if source has multiple distinct sections
- +1 slide for each major metaphor to visualize
- -1-2 slides if source is already concise
- Min: 8 slides (thematically unified essays), 12 slides (multi-topic). Max: 16 slides

---

## Example Output (Policy Argument)

```yaml
slide_count: 15
slide_sequence:
  - slide_number: 1
    role: "title"
    source_section: "intro"
    intensity: 3
    notes: "Magazine format with ISSUE badge, dam/infrastructure image"
  - slide_number: 2
    role: "hook"
    source_section: "intro"
    intensity: 3
    notes: "Coffee shop couple - establish human stakes"
  - slide_number: 3
    role: "build"
    source_section: "cistern"
    intensity: 4
    notes: "Financial sleight of hand - checks vs. concrete"
  - slide_number: 4
    role: "evidence"
    source_section: "cistern"
    intensity: 4
    notes: "Cistern diagram - core system explanation"
  - slide_number: 5
    role: "build"
    source_section: "vetocracy"
    intensity: 4
    notes: "Vetocracy as valve control"
  - slide_number: 6
    role: "evidence"
    source_section: "vetocracy"
    intensity: 4
    notes: "Price vs. value dichotomy"
  - slide_number: 7
    role: "peak"
    source_section: "lag-time"
    intensity: 4
    notes: "Historical revelation - 40-year lag"
  - slide_number: 8
    role: "reframe"
    source_section: "reframe"
    intensity: 4
    notes: "Induced demand → restored agency"
  - slide_number: 9
    role: "reframe"
    source_section: "reframe"
    intensity: 4
    notes: "Jevons Paradox as 'beautiful trap'"
  - slide_number: 10
    role: "build"
    source_section: "digital"
    intensity: 3
    notes: "Sensory vision - ozone and salt"
  - slide_number: 11
    role: "evidence"
    source_section: "digital"
    intensity: 4
    notes: "Cloud needs copper and concrete"
  - slide_number: 12
    role: "peak"
    source_section: "digital"
    intensity: 5
    notes: "Crisis visualization - transformer explosion"
  - slide_number: 13
    role: "build"
    source_section: "digital"
    intensity: 4
    notes: "Unified theory - housing and AI same problem"
  - slide_number: 14
    role: "transition"
    source_section: "resolution"
    intensity: 3
    notes: "Unfreezing - change beginning"
  - slide_number: 15
    role: "resolution"
    source_section: "resolution"
    intensity: 4
    notes: "Key turning, air moving, return to couple"

arc_visualization:
  type: "5-part"
  peaks: [7, 12]
  nadir: null
  concession: null
```

---

## Comparison Marking

When the source text contains explicit A-vs-B contrasts (e.g., two philosophies, two approaches, two traditions), mark those slides as `evidence` with a note indicating the comparison:

```yaml
- slide_number: 9
  role: "evidence"
  source_section: "three_schools"
  intensity: 4
  notes: "comparison: Zen simplicity vs Taoist naturalism vs Confucian ceremony"
```

For meditative arcs, Part III (Embodiment) often contains comparative slides where abstract ideas are contrasted through concrete examples.

---

## Validation Checklist

Before submitting output, verify:

- [ ] Slide count within 8-16 range (8-10 for unified essays, 12-16 for multi-topic)
- [ ] First slide is `title` role
- [ ] Last slide is `resolution` role
- [ ] Intensity values are 1-5
- [ ] Peak slides have intensity 4-5
- [ ] All source sections mapped to at least one slide
- [ ] Arc type matches genre
- [ ] Peak/nadir/concession positions match arc type
