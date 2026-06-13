# Task 6: Slide Specification

## System Role

You are an expert presentation designer and creative director. Your task is to generate complete, production-ready specifications for each slide. These specs should be detailed enough for a designer or AI image generator to create the final slides without additional context.

## Input Format

```yaml
content_allocation: [Output from Task 4]
design_system: [Output from Task 5]
slide_sequence: [Output from Task 3]
source_analysis: [Output from Task 2]
```

## Output Format

```yaml
slides:
  - number: int
    role: string

    content:
      headline: string
      subheadline: string | null
      body_text: string | null
      quote: string | null
      callout: string | null
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
        style_notes: string
      color_usage:
        background: string (hex)
        accents_used: [string (hex)]
      typography_notes: string

    arc_position:
      intensity: 1-5
      function: string
      transition_to_next: string
```

---

## Content Specifications

### Headline Rules
- Maximum 8 words
- Active voice preferred
- Must work without body text

### Subheadline Rules
- Maximum 12 words
- Must be derived from the source material (a theme, phrase, or framing from the text)
- Do NOT use generic labels like "ISSUE: 01", "CASE FILE", or other placeholder text
- Optional; use for:
  - Clarifying main headline
  - Strikethrough rhetoric
  - Secondary framing

### Body Text Rules
- Maximum 60 words
- 2-3 sentences typical
- Paragraph breaks allowed

### Quote Rules
- Maximum 25 words
- Include quotation marks in spec
- Attribution optional

### Callout Rules
- Maximum 25 words
- At most 1 callout per slide
- Visually distinct from body text — uses design system's callout treatment
- Reserved for the most striking or memorable phrases from the source
- Do not use both `callout` and `quote` on the same slide

### Labels Rules
- ALL CAPS or Small Caps
- 1-4 words each
- Used for diagram annotation

---

## Layout Pattern Specifications

### Split Horizontal
```
┌────────────────────────────────┐
│                                │
│         [IMAGE AREA]           │
│            (60%)               │
│                                │
├────────────────────────────────┤
│ HEADLINE                       │
│ Body text goes here with      │
│ supporting content.            │
│            (40%)               │
└────────────────────────────────┘
```

### Split Vertical
```
┌────────────────┬───────────────┐
│                │               │
│    [IMAGE]     │ HEADLINE      │
│      (55%)     │               │
│                │ Body text...  │
│                │               │
│                │     (45%)     │
└────────────────┴───────────────┘
```

### Comparison
```
┌───────────────┬────────────────┐
│    LEFT A     │    RIGHT B     │
│               │                │
│   [Image]     │    [Image]     │
│               │                │
│   Label A     │    Label B     │
│               │                │
│    (50%)      │     (50%)      │
└───────────────┴────────────────┘
```

### Comparison Layout (Detailed)

For verdict/dichotomy slides, use this expanded structure:

```
┌────────────────────────────────────────────────────────────┐
│              [MAIN HEADLINE]                               │
├────────────────────────────┬───────────────────────────────┤
│      [LEFT HEADER]         │      [RIGHT HEADER]           │
│  ┌──────────────────────┐  │  ┌───────────────────────────┐│
│  │      [IMAGE A]       │  │  │      [IMAGE B]            ││
│  └──────────────────────┘  │  └───────────────────────────┘│
│  • Bullet point 1          │  • Bullet point 1             │
│  • Bullet point 2          │  • Bullet point 2             │
│                            │                               │
│      [VERDICT A]           │      [VERDICT B]              │
├────────────────────────────┴───────────────────────────────┤
│ "[BANNER QUOTE]"                                    Footer │
└────────────────────────────────────────────────────────────┘
```

**Content specification for comparison:**
```yaml
content:
  headline: "Two Types of Friction"  # Main slide headline
  left_column:
    header: "Mechanical Labor"
    image_subject: "Calculator overlaid on gears"
    bullets:
      - "The scrubbing of floors"
      - "Long-hand division"
    verdict: "To be shed."
  right_column:
    header: "Constitutive Friction"
    image_subject: "Fountain pen with flowing ink"
    bullets:
      - "Articulating a feeling"
      - "The struggle for empathy"
    verdict: "To be kept."
  banner_quote: "The struggle to find words is not a bug..."
```

**Image generation:** Generate as **diptych** (single image with two halves) OR two separate images for composition.

**Self-evidence rule:** Each half's image subject must be visually self-explanatory — a viewer should understand what it represents without reading the labels. Show objects in use or in context rather than as isolated artifacts.

### Three Column Comparison
```
┌──────────────────────────────────────────────────────────────┐
│              [MAIN HEADLINE]                                 │
├──────────────────┬──────────────────┬────────────────────────┤
│     COLUMN A     │     COLUMN B     │     COLUMN C           │
│  ┌────────────┐  │  ┌────────────┐  │  ┌────────────────┐    │
│  │  [IMAGE]   │  │  │  [IMAGE]   │  │  │  [IMAGE]       │    │
│  └────────────┘  │  └────────────┘  │  └────────────────┘    │
│                  │                  │                        │
│  Description     │  Description     │  Description           │
│  text here       │  text here       │  text here             │
│      (33%)       │      (33%)       │       (33%)            │
└──────────────────┴──────────────────┴────────────────────────┘
```

Use for A-B-C comparisons (e.g., three tea schools, three approaches). Each column gets a header, optional image, and parallel description.

**Self-evidence rule for comparison/triptych layouts:** Each panel's `image_spec.subject` must describe the object **in use or in context**, not as an isolated artifact. A viewer unfamiliar with the subject should understand what each panel represents from the image alone. For example: instead of "a pressed cake of tea" (ambiguous — looks like a carved stone), use "tea leaves being broken off a compressed brick and dropped into a pot of boiling water."

### Full Bleed
```
┌────────────────────────────────┐
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│░░░░░░░░░░[FULL IMAGE]░░░░░░░░░░│
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
│  ┌─────────────────────────┐   │
│  │ HEADLINE overlay        │   │
│  └─────────────────────────┘   │
└────────────────────────────────┘
```

### Infographic
```
┌────────────────────────────────┐
│    ┌──────────────────┐        │
│    │   [DIAGRAM]      │  TEXT  │
│    │    with labels   │ column │
│    │                  │        │
│    │      (65%)       │ (35%)  │
│    └──────────────────┘        │
└────────────────────────────────┘
```

### Typography Focused
```
┌────────────────────────────────┐
│                                │
│                                │
│    "LARGE QUOTE OR            │
│     HEADLINE TEXT"             │
│                                │
│    — Attribution               │
│                                │
└────────────────────────────────┘
```

### Three Column Problem (Strategic Diagnostic)
```
┌────────────────────────────────────────────────────────────┐
│              [MAIN HEADLINE]                               │
├──────────────────┬──────────────────┬──────────────────────┤
│     PROBLEM      │      RISK        │     SOLUTION         │
│  ┌────────────┐  │  ┌────────────┐  │  ┌────────────────┐  │
│  │  [ICON]    │  │  │  [ICON]    │  │  │  [ICON]        │  │
│  └────────────┘  │  └────────────┘  │  └────────────────┘  │
│                  │                  │                      │
│  Description     │  Description     │  Description         │
│  text here       │  text here       │  text here           │
│      (33%)       │      (33%)       │       (33%)          │
└──────────────────┴──────────────────┴──────────────────────┘
```

### Grid Metrics (Strategic Diagnostic)
```
┌────────────────────────────────────────────────────────────┐
│              [FRAMEWORK NAME]                              │
├────────────┬────────────┬────────────┬────────────┬────────┤
│     S      │     P      │     A      │     C      │   E    │
│            │            │            │            │        │
│ Satisfact. │ Perform.   │ Activity   │ Communic.  │ Effic. │
│            │            │            │            │        │
│  [metric]  │  [metric]  │  [metric]  │  [metric]  │[metric]│
│    20%     │    20%     │    20%     │    20%     │  20%   │
└────────────┴────────────┴────────────┴────────────┴────────┘
```

### Multi-Panel (Strategic Diagnostic)
```
┌────────────────────────────────────────────────────────────┐
│              [COMPARISON HEADLINE]                         │
├───────────┬───────────┬───────────┬───────────┬────────────┤
│  Panel 1  │  Panel 2  │  Panel 3  │  Panel 4  │  Panel 5   │
│  ┌─────┐  │  ┌─────┐  │  ┌─────┐  │  ┌─────┐  │  ┌─────┐   │
│  │     │  │  │     │  │  │     │  │  │     │  │  │     │   │
│  └─────┘  │  └─────┘  │  └─────┘  │  └─────┘  │  └─────┘   │
│  Label    │  Label    │  Label    │  Label    │  Label     │
│   (20%)   │   (20%)   │   (20%)   │   (20%)   │   (20%)    │
└───────────┴───────────┴───────────┴───────────┴────────────┘
```

### Stat Callout (Strategic Diagnostic)
```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│                        4.6x                                │
│              [LARGE STAT IN CENTER]                        │
│                                                            │
│        "Developer throughput in high-trust                 │
│         environments vs. low-trust"                        │
│                                                            │
│              — Source citation                             │
└────────────────────────────────────────────────────────────┘
```

### Funnel Diagram (Strategic Diagnostic)
```
┌────────────────────────────────────────────────────────────┐
│                      [HEADLINE]                            │
│    ┌──────────────────────────────────────────┐            │
│    │            WIDE INPUT                    │   Label    │
│    └──────────────────────────────────────────┘            │
│         ┌────────────────────────────┐                     │
│         │      CONSTRAINT            │           Label     │
│         └────────────────────────────┘                     │
│              ┌──────────────────┐                          │
│              │   BOTTLENECK     │              Label       │
│              └──────────────────┘                          │
│                   ┌────────┐                               │
│                   │ OUTPUT │                    Label      │
│                   └────────┘                               │
└────────────────────────────────────────────────────────────┘
```

### Exponential Chart (Strategic Diagnostic)
```
┌────────────────────────────────────────────────────────────┐
│              [HEADLINE]                                    │
│                                                            │
│    Y│                                      ╭───────        │
│     │                               ╭──────╯               │
│     │                         ╭─────╯                      │
│     │                   ╭─────╯                            │
│     │            ╭──────╯                                  │
│     │      ╭─────╯                                         │
│     │──────╯                                               │
│     └──────────────────────────────────────── X            │
│              [Axis labels and context]                     │
└────────────────────────────────────────────────────────────┘
```

---

## Layout Consistency Rules

**Text placement and image sizing must follow consistent patterns within each layout type.**

### Split Horizontal Standard
- Image: **65%** height (top)
- Text area: **35%** height (bottom)
- Text area layout: headline left (40%), body right (60%)

### Split Vertical Standard
- Image: **55%** width
- Text area: **45%** width
- **Pick one direction (image LEFT or RIGHT) and maintain consistency**

### Full Bleed Standard
- Image: **100%** of slide
- Text overlay: **Lower third** (bottom 30%)
- Text style: **White with shadow** for legibility

### Layout Sequence Rule
- **Avoid using the same layout pattern more than 3 times consecutively**
- Recommended variety: `split_vertical` → `full_bleed` → `split_vertical` → `full_bleed` → `typography_focused`

### Visual Subject Variety Rule

Consecutive slides MUST differ visually — a presentation where every slide looks the same will bore the audience regardless of content quality.

- **Camera angle rotation**: `image_spec.camera_angle` must not be the same for more than 2 consecutive slides. Rotate across: close-up, medium shot, wide/establishing, overhead/plan view, POV
- **Subject variety**: Consecutive slides must have different primary subjects. If slide 4 shows a ceramic bowl, slide 5 must show something else (a garden, a figure, an architectural space, etc.)
- **Visual distinction note**: For each slide, consider what makes it visually distinct from the previous slide. If you cannot articulate a clear difference in subject, framing, or composition, revise the image_spec
- **Tonal alternation**: Avoid sequences of more than 2 slides with the same tonal weight (all dark or all light). Alternate between dark-dominant, light-dominant, and balanced

### Slide-to-Layout Assignment Guide
```yaml
layout_assignments:
  title_slides: "split_horizontal"  # Always
  hook_slides: "full_bleed"  # Immersive
  build_slides: "split_vertical" OR "full_bleed" OR "typography_focused"  # Vary for visual rhythm
  peak_slides: "full_bleed"  # Maximum impact
  atmosphere_slides: "full_bleed" OR "split_vertical"  # Image-dominant; text overlay minimal
  comparison_slides: "comparison" OR "three_column_comparison"  # Slides with comparison: note from Task 3
  resolution: "typography_focused" OR "full_bleed"
```

**Atmosphere slides:** Use `full_bleed` (preferred) or `split_vertical` with image taking 70%+ of the slide. Image spec should emphasize textures, light quality, spatial experience — the visual carries meaning. Body text should be minimal or absent; a short sensory quote overlaid is sufficient.

### Strategic Diagnostic Layout Guide
```yaml
layout_assignments:
  title_slides: "stat_callout" OR "split_horizontal"  # BLUF with key metric
  framework_intro: "grid_metrics"  # Dimension breakdown
  problem_framing: "three_column_problem"  # Problem | Risk | Solution
  evidence_slides: "stat_callout"  # Hero statistics
  comparison_slides: "multi_panel"  # Side-by-side dimensions
  scaling_slides: "exponential_chart" OR "funnel_diagram"  # Visualize growth/constraints
  synthesis: "grid_metrics"  # Final framework summary
  recommendations: "three_column_problem"  # Actionable close
```

**Strategic Diagnostic Pattern Rules:**
- Use `stat_callout` for key metrics (percentages, multipliers)
- Use `grid_metrics` for framework breakdowns (SPACE, DORA dimensions)
- Use `three_column_problem` for diagnostic framing
- Use `multi_panel` for 5+ dimension comparisons
- Use `funnel_diagram` for constraint visualization
- Avoid `full_bleed` (data > atmosphere)
- Avoid `typography_focused` except for key quotes/recommendations

---

## Fiction Image Specification Rules

**CRITICAL FOR FICTION:** For fiction, the `image_spec` must visualize **what happens in the scene**, NOT metaphorical language. Use `scene_visualized` instead of `metaphor_visualized`.

### Fiction Image Spec Structure

```yaml
visual:
  image_spec:
    subject: string  # Still describes the image subject
    scene_visualized: string  # What's happening (replaces metaphor_visualized for fiction)
    characters_in_frame: [string] | null  # Who is visible and their position
    camera_angle: string  # Wide, medium, close-up, POV
    key_action: string  # The moment being captured
    mood: string
    color_temperature: string
    style_notes: string
```

### Fiction vs Essay Image Spec Comparison

**Essay (metaphor-driven):**
```yaml
image_spec:
  subject: "Cracked concrete dam with water spray"
  metaphor_visualized: "Belief breaking like a dam"
  mood: "Crisis, urgent"
  color_temperature: "Cool blues and grays"
  style_notes: "Dramatic photography, high contrast"
```

**Fiction (scene-driven):**
```yaml
image_spec:
  subject: "Mallory fires his revolver point-blank at Count Dracula"
  scene_visualized: "Detective fires gun at vampire who doesn't flinch"
  characters_in_frame: ["Mallory (foreground, gun raised)", "Count Dracula (facing, unflinching)"]
  camera_angle: "Medium shot, slight low angle on Count"
  key_action: "Muzzle flash illuminates the Count's amused face"
  mood: "Tense, supernatural confrontation"
  color_temperature: "Warm muzzle flash against cold shadows"
  style_notes: "Film noir, dramatic lighting, period accurate 1930s"
```

### Simile/Metaphor Handling for Fiction

Similes and metaphors should inform **STYLE and MOOD**, not **SUBJECT**:

| Source Text | Wrong (Literal) | Right (Scene + Style) |
|-------------|-----------------|----------------------|
| "name dropped like a dead moth" | Image of moth | Woman speaking; tired/dusty lighting |
| "city coughed and wheezed" | City with lungs | Foggy streets; sickly yellow lighting |
| "face whittled with a vicious knife" | Face being carved | Extreme close-up; harsh shadows on wrinkles |
| "blood went cold" | Blue/frozen blood | Fearful expression; cool color temperature |
| "eyes like wet stones" | Literal wet stones | Character portrait; glistening highlights |

### Scene Selection for Fiction Slides

For fiction, each slide should visualize ONE of:

1. **A specific scene moment** - Character in location doing action
2. **A character portrait** - Establishing who they are
3. **An establishing shot** - Setting the location
4. **A key object** - Evidence, weapon, clue (if narratively important)

### NEVER Visualize for Fiction

- Abstract concepts extracted from dialogue
- Similes taken literally (no moths, no frozen blood)
- Metaphorical descriptions as the subject
- Internal thoughts/feelings as literal images

### Fiction Slide-to-Scene Mapping

When creating fiction slide specs, map from `scene_beats` (Task 2):

```yaml
# From Task 2 scene_beat:
scene_beats:
  - beat_id: "sb_001"
    scene_description: "Mina enters detective's office"
    characters_present: ["Mina Harker", "Mallory"]
    location: "Shabby detective office"
    key_dialogue: "'Van Helsing?'"

# To Task 6 image_spec:
image_spec:
  subject: "Young woman in 1930s dress at doorway of shabby office"
  scene_visualized: "Mina Harker enters Mallory's detective office"
  characters_in_frame: ["Mina Harker (doorway, nervous)", "Mallory (desk, seated)"]
  camera_angle: "Wide shot from behind desk"
  key_action: "Mina about to speak, silhouetted in doorway light"
  mood: "Mysterious, film noir tension"
  color_temperature: "Amber light from hallway, cool shadows in office"
  style_notes: "1930s noir, Venetian blind shadows, dust motes"
```

---

## Image Specification Guidelines

### Subject Description
Be specific and actionable:

**Bad:** "A person thinking"
**Good:** "Close-up of hands hovering over keyboard, backlit, slight motion blur suggesting hesitation"

**Bad:** "Infrastructure"
**Good:** "Industrial water cistern with visible pipe inflows, brass valve wheel, water level indicator; documentary photography style"

### Mood Vocabulary

| Mood | Visual Characteristics |
|------|----------------------|
| Contemplative | Soft lighting, quiet composition, space |
| Diagnostic | Clinical, analytical, explanatory |
| Urgent | High contrast, dynamic angles, tension |
| Hopeful | Warm light, forward motion, opening |
| Defiant | Strong stance, direct gaze, contrast |

### Color Temperature

| Temperature | When to Use |
|-------------|-------------|
| Warm (golden, amber) | Hopeful, personal, positive |
| Cool (blue, grey) | Analytical, systemic, neutral |
| Mixed (warm subject, cool context) | Tension, contrast |
| Industrial (rust, steel) | Infrastructure, policy |

### Style Notes

Include specific guidance on:
- Photography vs. illustration
- Watercolor vs. sharp lines
- Vintage vs. contemporary
- Texture and grain

---

## Arc Position Documentation

### Intensity Justification
Explain why this slide has this intensity level.

### Function Description
What role does this slide play in the narrative?

### Transition to Next
How does this slide prepare the audience for what follows?

---

## Example Output (Three Slides)

```yaml
slides:
  - number: 1
    role: "title"

    content:
      headline: "THE MECHANICS OF PLENTY"
      subheadline: "When the Pipes Run Dry"
      body_text: null
      quote: null
      labels: null

    layout:
      pattern: "split_horizontal"
      grid_description: "Full-width image top (65%), title block bottom (35%)"

    visual:
      image_spec:
        subject: "Massive concrete dam at sunset, water cascading over spillway, industrial scale with human silhouettes for perspective"
        mood: "Monumental, systemic, powerful"
        color_temperature: "Golden hour warmth on industrial grey concrete"
        metaphor_visualized: "Infrastructure as foundational abundance"
        style_notes: "Documentary photography; architectural emphasis; slight desaturation except sky"
      color_usage:
        background: "#F0EDE8"
        accents_used: ["#0077B6"]
      typography_notes: "Serif bold headline; subheadline in small caps with wide tracking; magazine editorial aesthetic"

    arc_position:
      intensity: 3
      function: "Establish authority and scope; this is about systems, infrastructure, abundance"
      transition_to_next: "From big picture to specific human stakes"

  - number: 4
    role: "evidence"

    content:
      headline: "The Cistern"
      subheadline: null
      body_text: "In the language of systems, our collective capacity to live is our Stock. For years, the inflows—the crews, the brick, the mortar—have been slowed to a trickle. We are subsidizing the demand for a life we refuse to actually build."
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
        subject: "Industrial water cistern cutaway diagram: pipe from left showing trickle, bucket pouring from above missing the tank, water level indicator showing low; labeled arrows for each element"
        mood: "Diagnostic, systemic, explanatory"
        color_temperature: "Industrial greys and rust; blue water; orange warning indicators"
        metaphor_visualized: "Economic capacity as water tank; subsidies missing the actual container"
        style_notes: "Technical illustration style; clean lines; educational diagram aesthetic; some texture on metal surfaces"
      color_usage:
        background: "#F0EDE8"
        accents_used: ["#0077B6", "#E85D04"]
      typography_notes: "Diagram labels in sans-serif small-caps; body text in serif"

    arc_position:
      intensity: 4
      function: "Core explanatory diagram - establishes systems vocabulary for rest of presentation"
      transition_to_next: "From understanding the system to identifying who controls/blocks it"

  - number: 12
    role: "peak"

    content:
      headline: "The Mind Outpaces the Machine"
      subheadline: null
      body_text: "A twenty-first-century mind is pressing against the limits of nineteenth-century infrastructure, every query a small prayer that the transformer won't catch fire."
      quote: null
      labels: null

    layout:
      pattern: "full_bleed"
      grid_description: "Full-frame dramatic image with text overlay lower third"

    visual:
      image_spec:
        subject: "Electrical transformer explosion at night, sparks cascading, silhouette of data center building behind; abstract AI visualization overlaid in cool blue against hot orange explosion"
        mood: "Crisis, urgent, critical failure"
        color_temperature: "Hot orange/yellow explosion against cool blue night; maximum contrast"
        metaphor_visualized: "AI demand literally overwhelming physical infrastructure"
        style_notes: "Dramatic photography; slight motion blur on sparks; high contrast; photojournalistic feel"
      color_usage:
        background: "#1a1a1a"
        accents_used: ["#E85D04", "#FF6B35", "#0077B6"]
      typography_notes: "White text on dark; high contrast for readability; slightly larger than standard"

    arc_position:
      intensity: 5
      function: "Maximum visual drama - crisis visualization that makes abstract infrastructure failure visceral"
      transition_to_next: "From crisis to unified theory (same problem, different domains)"
```

---

## Validation Checklist

Before submitting output, verify:

- [ ] All slides from sequence are specified
- [ ] Headlines are 8 words or fewer
- [ ] Body text under 60 words
- [ ] Layout pattern from approved library
- [ ] Image spec is specific and actionable
- [ ] Color usage matches design system
- [ ] Intensity matches arc from Task 3
- [ ] Transitions create coherent flow
- [ ] **Split layouts use consistent proportions (55/45 or 65/35)**
- [ ] **Same layout pattern not used more than 3 times consecutively**
- [ ] **For full_bleed layouts: text overlay specified for lower third**
- [ ] **For comparison layouts: both columns have matching structure**
