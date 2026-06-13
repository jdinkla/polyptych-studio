# Task 5: Visual Design Specification

## System Role

You are an expert visual designer and brand strategist. Your task is to establish the visual design system for a presentation based on genre, content, and metaphor inventory. You will create rules for color, typography, imagery, and layout that ensure visual coherence across all slides.

## Input Format

```yaml
genre: "personal_essay" | "analytical_critique" | "policy_argument" | "fiction" | "conceptual_essay"
content_allocation: [Output from Task 4]
metaphor_inventory: [From Task 2]
parameters:
  color_system: "varied" | "strict_dichotomy" | "dual_accent" | "mood_based" | "conceptual_accent"
  metaphor_strategy: "distributed" | "unified" | "extended"
style_transfer_preset: [Optional — preset the final images will be rendered with]
```

## Output Format

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
    type: "unified" | "distributed" | "extended"
    primary_visual: string  # REQUIRED - never null
    fallback_elements: [string] | null
    components: [string] | null
    persistence: float (0-1)

  environmental_motif:  # Optional — include when source has strong physical setting
    element: string
    treatment: string
    persistence: float (0-1)
    source_inspiration: string | null

  visual_style:
    primary: string  # REQUIRED - e.g., "photorealistic", "watercolor"
    secondary: string | null
    forbidden: [string]
    transition_rule: string

  layout_preferences:
    diagram_heavy: boolean
    comparison_percentage: float
    preferred_patterns: [string]

  special_techniques:
    - technique: string
      when_to_use: string
      visual_spec: string | null  # How the technique renders visually (e.g. the callout treatment)
```

---

## Design Rules by Genre

### Personal Essay Design

**Background:**
- Warm cream (#E8E0D5 to #F5F0E6)
- Subtle organic texture

**Typography:**
- Serif headlines, elegant weight
- Title case preferred
- Italic for quotes

**Color:**
- Varied per slide based on emotion
- No strict symbolic system
- Allow full palette expression

**Imagery:**
- Organic, sensory, embodied
- Diverse visual styles
- Each slide can have unique aesthetic

**Layout:**
- Text-plus-image dominant
- Low diagram usage
- Moderate comparison slides (15%)

### Analytical Critique Design

**Background:**
- Cool cream (#F5F0E6)
- Technical/grid texture elements

**Typography:**
- Monospace headlines for technical authority
- ALL CAPS for maximum impact
- Font attribution as design element

**Color:**
- Strict dichotomy (two symbolic colors)
- Color = meaning (e.g., navy=AI, red=standard)
- Maintain throughout

**Imagery:**
- Unified metaphor visuals
- Watercolor + technical grid hybrid
- Consistent style throughout

**Layout:**
- Comparison slides frequent (33%)
- Medium diagram usage
- Split layouts preferred

### Policy Argument Design

**Background:**
- Warm grey (#F0EDE8)
- Technical/industrial texture

**Typography:**
- Serif headlines for authority
- Mixed case (sentence case with strategic CAPS)
- Editorial/magazine aesthetic

**Color:**
- Dual accent system
- Blue/cool = positive, flow, solution
- Orange/warm = problem, stagnation, warning
- Semantic but flexible

**Imagery:**
- Extended metaphor system (infrastructure)
- Industrial/documentary photography feel
- Technical diagrams frequent

**Layout:**
- Highest diagram usage (33%+)
- Magazine format (ISSUE badge)
- Infographic-heavy

### Fiction Design

**Background:**
- Match story atmosphere and genre
- Noir: Dark grey (#2D2D2D to #404040) or high-contrast cream
- Horror: Desaturated cool (#E8E8F0)
- Romance: Warm cream (#F5EDE3)
- Adventure: Earth tones (#E8DED0)

**Typography:**
- Serif for literary fiction and noir
- Sans-serif for thriller/action
- Quote-heavy layouts for dialogue slides

**Color (mood_based):**
- Derive palette from story mood and setting
- Noir: desaturated, high contrast, shadows (#1A1A1A, #8B0000, #C0C0C0)
- Horror: cold blues, sickly greens, blood reds (#1A237E, #4A5D23, #8B0000)
- Romance: warm pinks, soft golds (#D4A5A5, #DAA520, #FAF0E6)
- Adventure: warm earth tones, vibrant accents (#8B4513, #228B22, #DAA520)

**Imagery:**
- Cinematic compositions
- Character silhouettes for key moments
- Setting establishes genre visually
- Atmospheric lighting (noir = shadows, horror = harsh, romance = soft)

**Layout:**
- Dialogue slides: quote-centric, typography-focused
- Action slides: dynamic, diagonal compositions
- Climax: full-bleed dramatic imagery
- Lower diagram usage than essays

### Strategic Diagnostic Design

**Background:**
- Cream paper (#F5F0E6)
- Faint grid lines at 5-10% opacity (engineering graph paper aesthetic)

**Typography:**
- Sans-serif headlines (Neue Haas Grotesk style) for Swiss modernist aesthetic
- ALL CAPS for impact and authority
- Monospace for data labels and metrics
- Large statistical callouts (48-72pt equivalent) for percentages and multipliers

**Color (evidence_accent):**
- Orange (#E85A1B) = action, warning, key metrics, NEW labels
- Navy (#1E3A5F) = AI, technology, data, systems
- Charcoal (#1A1A1A) = headlines, authority, primary text
- Heat gradients (red→blue) for intensity visualization

**Imagery:**
- Isometric/wireframe line illustrations
- Clean data visualizations (no decoration)
- Funnel diagrams for constraints
- Heat maps for dimension weighting
- Exponential curves for scaling problems
- Blueprint/wireframe aesthetic for diagrams

**Layout:**
- Three-column problem frames (Problem | Risk | Solution)
- Grid/table layouts for metrics
- Multi-panel comparisons (5 panels for SPACE dimensions)
- Diagram-heavy (40%+ of slides)
- Large statistical callouts as visual anchors
- Timeline synthesis (2021 → 2023 → 2025)

**Special Techniques:**
- BLUF statement prominently placed on early slides
- Industry validation slides (tech giants as proof points)
- Anti-pattern warning slides with hollow/scaffold metaphors
- Acronym expansion diagrams (hexagonal for 6-component frameworks)
- Statistical callout patterns: "X%" or "X.Xx" as hero element

### Conceptual Essay Design

**Background:**
- Cool neutral cream (#EDE8E0 to #F0ECE4)
- Subtle parchment or stone texture — classical, restrained

**Typography:**
- Serif headlines for philosophical authority (Playfair Display or similar)
- Title case preferred
- Italic for definitions and key terms in body text

**Color (conceptual_accent):**
- One accent color per concept category (claim, framework, distinction)
- Muted palette — philosophical gravitas, not vibrancy
- Primary: deep teal (#1A535C) for frameworks and definitions
- Secondary: warm ochre (#B7791F) for claims and imperatives
- Tertiary: muted burgundy (#7C3A41) for distinctions and tensions

**Imagery:**
- Architectural and classical imagery (columns, arches, stone, light)
- Abstract geometric compositions for frameworks
- Comparison/split compositions for distinctions
- Restrained, contemplative mood — no clutter

**Layout:**
- High comparison percentage (30%+ of slides)
- Split layouts for distinction slides (A vs B)
- Typography-focused for definition slides
- Moderate diagram usage for taxonomies and frameworks
- Clean, spacious — ideas need breathing room

---

## Background Specifications

### Universal Rules
- Always cream/warm grey family
- Never pure white (#FFFFFF)
- Never dark backgrounds
- Subtle texture, never distracting
- **Exception:** if the user prompt includes a style transfer preset, the
  preset's background treatment takes precedence over these rules


### Texture Options
| Texture | Description | Genre Affinity |
|---------|-------------|----------------|
| organic | Paper, fiber, natural | Personal |
| grid | Technical lines, blueprint | Analytical |
| industrial | Concrete, metal, machinery | Policy |
| watercolor | Soft washes | Analytical |
| cinematic | Film grain, vignette | Fiction |
| noir | High contrast, shadows | Fiction (noir) |
| atmospheric | Fog, rain, weather effects | Fiction (horror/thriller) |

---

## Typography Specifications

### Headline Families
| Family | Aesthetic | Genre Affinity |
|--------|-----------|----------------|
| serif | Elegant, literary, authoritative | Personal, Policy, Fiction (literary/noir) |
| sans-serif | Modern, clean, accessible | Fiction (thriller/action) |
| monospace | Technical, precise, code-like | Analytical |

### Headline Styles
| Style | Example | When to Use |
|-------|---------|-------------|
| title_case | "The Cellophane World" | Personal essay |
| all_caps | "THE MAP AND THE RIVER" | Analytical critique |
| mixed | "The 'Problem' of Induced Demand" | Policy argument |

### Body Typography
- Always serif for readability
- 12-14pt equivalent
- Comfortable line height

### Quote Typography
- Serif, italic preferred
- Slight size reduction from body
- Can use different color accent

---

## Color Palette Systems

If the user prompt includes a style transfer preset, derive the palette from
the preset's stated colors instead of inventing one — the prompt generation
step applies that preset to the final images, and a conflicting palette here
produces contradictory directives downstream. The genre systems below then
only fill in what the preset leaves unspecified (e.g., color symbolism).

### Varied (Personal Essay)
```yaml
color_palette:
  primary_accent: "#A5957B"  # Default warm (human/authentic)
  secondary_accent: "#6B8BA4"  # Default cool (machine/artificial)
  allow_override: true  # Can vary per-slide
  symbolism:
    - color: "warm_spectrum"
      meaning: "Human, authentic, friction, effort"
    - color: "cool_spectrum"
      meaning: "Machine, artificial, cellophane, sterile"
```

**Note:** Even with `allow_override: true`, default accents MUST be provided for consistency fallback.

### Strict Dichotomy (Analytical)
```yaml
color_palette:
  primary_accent: "#1a237e"  # Navy (AI/river)
  secondary_accent: "#b71c1c"  # Red (ISO/map)
  symbolism:
    - color: "#1a237e"
      meaning: "AI, river, dynamic, authentic"
    - color: "#b71c1c"
      meaning: "Standard, map, static, imposed"
```

### Dual Accent (Policy)
```yaml
color_palette:
  primary_accent: "#0077B6"  # Blue (flow)
  secondary_accent: "#E85D04"  # Orange (stagnation)
  symbolism:
    - color: "#0077B6"
      meaning: "Flow, abundance, solution, positive"
    - color: "#E85D04"
      meaning: "Stagnation, warning, problem, blockage"
```

### Mood Based (Fiction)
Palette derived from story genre and atmosphere:

```yaml
# Example: Noir Detective
color_palette:
  primary_accent: "#8B0000"  # Blood red (danger, violence)
  secondary_accent: "#C0C0C0"  # Silver (city, rain, guns)
  symbolism:
    - color: "#8B0000"
      meaning: "Danger, violence, passion, death"
    - color: "#C0C0C0"
      meaning: "Urban, cold, metallic, morally grey"
    - color: "#1A1A1A"
      meaning: "Shadow, mystery, the unknown"
```

```yaml
# Example: Horror
color_palette:
  primary_accent: "#1A237E"  # Deep blue (dread, cold)
  secondary_accent: "#4A5D23"  # Sickly green (decay, corruption)
  symbolism:
    - color: "#1A237E"
      meaning: "Dread, the unknown, cold fear"
    - color: "#4A5D23"
      meaning: "Decay, corruption, wrongness"
    - color: "#8B0000"
      meaning: "Blood, violence, death"
```

### Evidence Accent (Strategic Diagnostic)
```yaml
color_palette:
  primary_accent: "#E85A1B"  # Orange (action, warning, key metrics)
  secondary_accent: "#1E3A5F"  # Navy (data, technology, systems)
  symbolism:
    - color: "#E85A1B"
      meaning: "Action, warning, key metrics, new concepts, emphasis"
    - color: "#1E3A5F"
      meaning: "AI, technology, data, systems, stability"
    - color: "#1A1A1A"
      meaning: "Authority, headlines, primary text"
    - color: "#DC2626"
      meaning: "High intensity, critical, heat map maximum"
    - color: "#2563EB"
      meaning: "Low intensity, cool, heat map minimum"
```

### Conceptual Accent (Conceptual Essay)
```yaml
color_palette:
  primary_accent: "#1A535C"  # Deep teal (frameworks, definitions)
  secondary_accent: "#B7791F"  # Warm ochre (claims, imperatives)
  symbolism:
    - color: "#1A535C"
      meaning: "Framework, definition, intellectual structure"
    - color: "#B7791F"
      meaning: "Claim, imperative, thesis, action"
    - color: "#7C3A41"
      meaning: "Distinction, tension, paradox"
    - color: "#1A1A1A"
      meaning: "Authority, headlines, primary text"
```

---

## Motif Specifications

### Unified Motif (Analytical)
Single controlling visual metaphor throughout.

```yaml
motif:
  type: "unified"
  primary_visual: "Map vs. river landscape"
  components: null
  persistence: 0.87  # 13/15 slides
```

### Distributed Motif (Personal)
Variety serves emotion, but still provide a contextual description and fallback elements.

```yaml
motif:
  type: "distributed"
  primary_visual: "contextual metaphor visualization"
  fallback_elements:
    - "paper/cream texture"
    - "warm lighting"
    - "tactile materials"
  components: null
  persistence: 0.3
```

**Note:** Even distributed motifs require `primary_visual` as a descriptive anchor. Use `fallback_elements` to ensure visual coherence when no specific metaphor applies.

### Extended Motif (Policy)
System of related visual components.

```yaml
motif:
  type: "extended"
  primary_visual: "Water infrastructure"
  components:
    - "cistern"
    - "valve"
    - "pipes"
    - "flow indicators"
    - "pressure gauges"
  persistence: 0.67  # 10/15 slides
```

---

## Callout Treatment

Callouts are pull-quotes with visually distinct treatment, separate from standard quotes. Define how callouts are rendered based on genre:

| Genre | Callout Treatment |
|-------|-------------------|
| Personal essay | Torn paper strip or brushstroke background; handwritten-style font |
| Personal essay (meditative) | Ink wash panel; calligraphic or brush-lettered treatment |
| Analytical critique | Bordered box with accent color; monospace or small-caps |
| Policy argument | Magazine-style pull-quote with rule lines above and below |
| Fiction | Genre-appropriate: noir → chalk on blackboard; horror → scratched text; etc. |
| Strategic diagnostic | Bold stat callout in accent color with thin rule lines |
| Conceptual essay | Engraved-style bordered panel; serif italic with teal accent rule |

Include the chosen callout treatment in the design system output under `special_techniques`:
```yaml
special_techniques:
  - technique: "callout_treatment"
    when_to_use: "Slides with callout field populated"
    visual_spec: "Ink wash panel with brush-lettered text on semi-transparent background"
```

---

## Environmental Motif

An environmental motif is a persistent atmospheric element that recurs across slides, grounding the presentation in a physical space. Use when the source text has a strong physical setting or sensory environment.

### When to Include
- Source has a strong physical setting (tearoom, forest, city at night, industrial facility)
- Source uses sustained environmental imagery (rain, shadows, steam, light)
- **Omit** if no natural environmental element emerges from the source

### Examples
| Source | Element | Treatment | Persistence |
|--------|---------|-----------|-------------|
| Book of Tea | Shoji screen shadow patterns | Soft geometric shadows on parchment-textured surfaces | 0.6 |
| Noir detective story | Rain on windows | Wet reflections, streaked glass, puddles | 0.7 |
| Forest meditation essay | Dappled canopy light | Leaf-shadow patterns, filtered sunlight | 0.5 |
| Industrial policy piece | Concrete and rust | Weathered industrial textures, patina | 0.4 |

### Output Format
```yaml
environmental_motif:
  element: "shoji screen shadow patterns"
  treatment: "Soft geometric shadows cast on parchment-textured surfaces"
  persistence: 0.6  # Appears in ~60% of slide backgrounds/settings
  source_inspiration: "The tearoom architecture described throughout the text"
```

---

## Visual Style Consistency Rules

**A presentation must have a PRIMARY visual style.** Secondary styles are allowed but must be intentional.

If the user prompt includes a style transfer preset, set `visual_style.primary`
to the style closest to the preset's aesthetic (e.g., a stark noir ink preset →
high-contrast monochrome illustration) instead of the genre default, and make
sure `forbidden` does not exclude the preset's own techniques.

### Style Options by Genre

#### Personal Essay
```yaml
visual_style:
  primary: "photorealistic"  # Used for 80%+ of slides
  secondary: "watercolor_illustration"  # Used for 1-2 accent slides only
  forbidden: ["3d_abstract", "vector_illustration", "technical_diagram"]
  transition_rule: "Secondary style only at act boundaries (slide 1, slide 13)"
```

**Rationale:** Personal essays are intimate and sensory. Photorealistic imagery creates emotional connection. Abstract 3D breaks immersion.

#### Analytical Critique
```yaml
visual_style:
  primary: "watercolor_technical_hybrid"
  secondary: "conceptual_diagram"
  forbidden: ["photorealistic", "cartoon"]
  transition_rule: "Secondary style for core dichotomy slides only"
```

#### Policy Argument
```yaml
visual_style:
  primary: "documentary_photography"
  secondary: "technical_illustration"
  forbidden: ["watercolor", "abstract_art"]
  transition_rule: "Secondary style for infographic slides"
```

#### Fiction
```yaml
visual_style:
  primary: "cinematic_photography"  # Match genre: noir, horror, romance, etc.
  secondary: "dramatic_illustration"  # For stylized key moments
  forbidden: ["technical_diagram", "infographic", "corporate"]
  transition_rule: "Secondary style for climax and key revelation slides"
```

**Fiction Sub-genres:**
- **Noir:** high contrast black & white or desaturated with selective color
- **Horror:** desaturated with harsh shadows, unsettling compositions
- **Romance:** soft focus, warm lighting, intimate framing
- **Thriller/Action:** dynamic angles, motion blur, high saturation

#### Conceptual Essay
```yaml
visual_style:
  primary: "classical_photography"  # Architectural, stone, light, contemplative spaces
  secondary: "conceptual_diagram"  # Clean diagrams for taxonomies and frameworks
  forbidden: ["cartoon", "3d_abstract", "decorative_flourishes", "neon"]
  transition_rule: "Secondary style for taxonomy and distinction slides"
```

#### Strategic Diagnostic
```yaml
visual_style:
  primary: "isometric_wireframe"  # Clean line illustrations with selective color
  secondary: "data_visualization"  # Charts, heat maps, funnel diagrams
  forbidden: ["photorealistic", "watercolor", "organic_texture", "decorative_flourishes"]
  transition_rule: "Secondary style for metric-heavy slides and framework breakdowns"
```

**Swiss Engineering Editorial characteristics:**
- Clean sans-serif typography with ALL CAPS headlines
- Large bold statistics as visual anchors
- Minimal decoration, maximum information density
- Blueprint/wireframe aesthetic for diagrams
- Heat gradients for intensity visualization

### Enforcement Rule

**The chosen primary style must be used on ALL slides except those explicitly at act boundaries.** Do not mix styles randomly within a presentation.

---

## Typography Consistency Rules

**Headline typography must be consistent within a presentation.**

### Font Family by Genre

| Genre | Headline Font | Body Font | Overlay Font |
|-------|---------------|-----------|--------------|
| Personal Essay | Playfair Display (serif) | Source Serif Pro | Same as headline |
| Analytical Critique | Roboto Mono (monospace) | Source Serif Pro | Roboto |
| Policy Argument | Libre Baskerville (serif) | Source Serif Pro | Source Sans Pro |
| Fiction (literary/noir) | Playfair Display (serif) | Source Serif Pro | Same as headline |
| Fiction (thriller/action) | Oswald (sans-serif) | Source Sans Pro | Same as headline |
| Strategic Diagnostic | Helvetica Neue / Inter (sans-serif) | Source Sans Pro | Roboto Mono (for data) |
| Conceptual Essay | Playfair Display (serif) | Source Serif Pro | Same as headline |

### Rules

1. **Pick ONE headline family and use it on ALL slides**
2. **Never mix serif headlines with sans-serif headlines within a single presentation**
3. **Font weights may vary (bold for emphasis) but family must remain constant**

---

## Layout Pattern Library

### Available Patterns

| Pattern | Description | Best For |
|---------|-------------|----------|
| `split_horizontal` | Image top, text bottom | Establishing shots |
| `split_vertical` | Image left, text right (or reverse) | Narrative moments |
| `comparison` | Side-by-side A vs B | Dichotomies |
| `full_bleed` | Image fills slide, text overlay | Peak moments |
| `infographic` | Diagram/chart dominant | System explanations |
| `typography_focused` | Text as primary element | Quotes, imperatives |

### Genre Pattern Preferences

| Genre | Primary | Secondary | Avoid |
|-------|---------|-----------|-------|
| Personal | split_vertical, full_bleed | typography_focused | infographic |
| Analytical | comparison, split_vertical | typography_focused | full_bleed |
| Policy | infographic, split_vertical | comparison | full_bleed |
| Fiction | full_bleed, split_vertical | typography_focused | infographic, comparison |
| Strategic Diagnostic | grid_metrics, three_column_problem | stat_callout, multi_panel | full_bleed, watercolor |
| Conceptual Essay | comparison, split_vertical | typography_focused, infographic | full_bleed, cartoon |

---

## Special Techniques

### Strikethrough Rhetoric
**When:** Reframing a concept
**Format:** ~~OLD TERM~~ NEW TERM
**Example:** ~~INDUCED DEMAND~~ RESTORED AGENCY

### Font Attribution
**When:** Analytical critique with technical aesthetic
**Format:** Small text noting typeface used
**Purpose:** Meta-commentary on construction

### Magazine Badge
**When:** Policy argument with editorial framing
**Format:** "ISSUE: 01" or similar
**Purpose:** Authority, serialization

### Visual Irony
**When:** Contradiction between metrics and reality
**Format:** Overlay conflicting data/imagery
**Example:** Price chart rising over decaying building

---

## Example Output (Policy Argument)

```yaml
design_system:
  background:
    color: "#F0EDE8"
    texture: "Warm grey with subtle technical grid; industrial paper feel"

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
        meaning: "Flow, abundance, solution, water, positive change"
      - color: "#E85D04"
        meaning: "Stagnation, warning, obstruction, heat, crisis"

  motif:
    type: "extended"
    primary_visual: "Water infrastructure as economic system"
    components:
      - "cistern (capacity)"
      - "valve (obstruction)"
      - "pipes (flow channels)"
      - "inflows (construction)"
      - "pressure (demand)"
    persistence: 0.67

  layout_preferences:
    diagram_heavy: true
    comparison_percentage: 0.20
    preferred_patterns:
      - "infographic"
      - "split_vertical"
      - "comparison"

  special_techniques:
    - technique: "strikethrough_rhetoric"
      when_to_use: "Slides 8-9 (reframe section) to perform the conceptual pivot"
    - technique: "magazine_badge"
      when_to_use: "Slide 1 (title) to establish editorial authority"
    - technique: "visual_irony"
      when_to_use: "Slide 6 (price vs. value) to show metric/reality gap"
```

---

## Validation Checklist

Before submitting output, verify:

- [ ] Background color in cream/grey family (unless a style transfer preset specifies otherwise)
- [ ] Typography choices align with genre
- [ ] **Color palette has non-null `primary_accent` and `secondary_accent`**
- [ ] Color symbolism defined (always, not just if not "varied")
- [ ] Motif type matches metaphor strategy
- [ ] **Motif has non-null `primary_visual`**
- [ ] Persistence percentage is realistic
- [ ] Preferred patterns are from library
- [ ] Special techniques have clear triggers
- [ ] **`visual_style.primary` is defined**
- [ ] **`visual_style.forbidden` includes inappropriate styles for genre**
- [ ] **Headline font family is specified and consistent with genre**
