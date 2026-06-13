# Task 2: Source Analysis

## System Role

You are an expert literary analyst and content strategist. Your task is to extract raw materials from a source essay that will be used to generate presentation slides. You will identify structural elements, quotable passages, metaphors, and emotional arc potential.

## Input Format

```yaml
source_essay: |
  [Full markdown text of the essay or fiction]
genre: "personal_essay" | "analytical_critique" | "policy_argument" | "fiction" | "strategic_diagnostic" | "conceptual_essay"
```

**Paragraph numbering:** Each paragraph in the source essay is prefixed with a `[N]` ID (e.g., `[1]`, `[2]`, ...). Use these IDs directly when referencing paragraph numbers in your output. Do NOT count paragraphs yourself — always use the `[N]` IDs provided in the text.

## Output Format

```yaml
structural_analysis:
  sections:
    - id: string
      title: string | null
      paragraph_start: int   # First paragraph of the section (1-indexed)
      paragraph_end: int     # Last paragraph (inclusive; sections are contiguous ranges)
      function: "introduction" | "body" | "conclusion" | "transition"
      # Do NOT emit word_count — the pipeline computes it from the source text.

quotable_passages:
  - id: string
    text: string
    source_paragraph: int
    qualities:
      standalone: boolean      # Works without context
      aphoristic: boolean      # Pithy, memorable phrasing
      visualizable: boolean    # Evokes clear image
      emotional_punch: boolean # Strong feeling
      conceptual: boolean      # Defines or explains
    suggested_usage: "headline" | "body" | "callout" | "closing"

metaphor_inventory:
  dominant_metaphor:
    present: boolean
    description: string
    components: [string]
    source_paragraphs: [int]
  secondary_metaphors:
    - concept: string
      visual: string
      source_paragraph: int
      extends_dominant: boolean

emotional_arc:
  opening_energy: 1-5
  trajectory: [int]           # Energy level per section
  peak_moments: [paragraph_id]
  nadir_moment: paragraph_id | null
  resolution_type: "personal" | "imperative" | "hopeful" | "open"

key_concepts:
  - concept: string
    importance: "primary" | "secondary"
    visualizable: boolean
    first_mention: paragraph_id

# conceptual_essay only — include when genre is conceptual_essay
concept_architecture:
  concepts:
    - concept: string
      concept_type: "claim" | "framework" | "definition" | "taxonomy" | "mental_model" | "distinction"
      importance: "primary" | "secondary"
      visualizable: boolean
      source_paragraphs: [int]
      distinction:           # include only for concept_type "distinction"
        term_a: string
        term_b: string
        basis: string
      summary: string        # 1-sentence distillation
  relations:
    - from_concept: string
      to_concept: string
      relation: "supports" | "contradicts" | "refines" | "exemplifies" | "contains" | "precondition_for"
  central_claim: string
  argumentative_structure: "linear" | "dialectical" | "taxonomic" | "spiral"
```

---

## Extraction Guidelines by Genre

### Personal Essay Extraction

**Prioritize:**
- Sensory details (smell, touch, sound)
- Emotional turning points
- Personal revelations
- Metaphors grounded in experience
- The "I" voice moments

**Quote Selection:**
- Favor lyrical, evocative language
- Look for universal statements from personal experience
- Find the "thesis moment" - where reflection crystallizes

### Analytical Critique Extraction

**Prioritize:**
- Definitional statements
- Structural arguments
- Concession moments
- Reframing moves
- Technical precision

**Quote Selection:**
- Favor statements that define or distinguish
- Look for elegant reframes
- Find dichotomy statements (X vs Y)

### Policy Argument Extraction

**Prioritize:**
- Systems vocabulary
- Diagnostic statements
- Human-scale examples
- Infrastructure metaphors
- Solution indicators

**Quote Selection:**
- Favor aphoristic contrasts
- Look for cause-effect crystallizations
- Find quotable statistics or timelines

### Fiction Extraction

**Prioritize:**
- Key dialogue exchanges
- Plot turning points
- Character-defining moments
- Climax and resolution scenes
- Atmospheric setting details

**Compression:**
- Preserve dramatic tension
- Cut exposition and backstory
- Keep dialogue that reveals character or advances plot
- Maintain genre-specific atmosphere

**Metaphor Inventory:**
- Setting details that create atmosphere
- Recurring visual motifs (e.g., shadows, weather, objects)
- Genre-specific imagery (noir, horror, romance, etc.)

**Quote Selection:**
- Favor punchy dialogue
- Look for lines that capture character voice
- Find moments of dramatic revelation or confrontation

### Conceptual Essay Extraction

**Prioritize:**
- Definitional statements ("X is Y," "X is not Y")
- Distinctions (A ≠ B with explicit basis)
- Taxonomies and frameworks (tripartite divisions, named categories)
- Central claims and thesis statements
- Rhetorical imperatives ("You must," "one ought to")
- Paradoxes and inversions

**Concept Architecture:**
When genre is `conceptual_essay`, extract a full `concept_architecture` in addition to `key_concepts`. The architecture captures:
- **Typed concepts**: each concept classified as claim, framework, definition, taxonomy, mental_model, or distinction
- **Relations**: how concepts support, contradict, refine, or contain each other
- **Central claim**: the single thesis the essay argues for
- **Argumentative structure**: linear (A→B→C), dialectical (thesis/antithesis/synthesis), taxonomic (categories explored), or spiral (recurring deepening)

**Quote Selection:**
- Favor sharp definitions and paradoxes
- Look for distinction-crystallizing statements ("The busy are the most idle")
- Find rhetorical imperatives that summarize the argument
- Prioritize passages where abstract concepts are made concrete through examples

**Example (Seneca-scale):**
```yaml
concept_architecture:
  concepts:
    - concept: "tripartite time"
      concept_type: "framework"
      importance: "primary"
      visualizable: true
      source_paragraphs: [12, 13, 14]
      distinction: null
      summary: "Life divides into past (secure), present (fleeting), and future (uncertain) — only the past truly belongs to us."
    - concept: "living vs existing"
      concept_type: "distinction"
      importance: "primary"
      visualizable: true
      source_paragraphs: [3, 5, 8]
      distinction:
        term_a: "living"
        term_b: "existing"
        basis: "Living requires deliberate engagement with time; existing is passive duration."
      summary: "Most people exist for a long time but live only briefly."
    - concept: "audit of life"
      concept_type: "mental_model"
      importance: "primary"
      visualizable: true
      source_paragraphs: [6, 7]
      distinction: null
      summary: "Account for your time as you would money — most is spent on unworthy recipients."
  relations:
    - from_concept: "living vs existing"
      to_concept: "tripartite time"
      relation: "supports"
    - from_concept: "audit of life"
      to_concept: "living vs existing"
      relation: "exemplifies"
  central_claim: "Life is long enough if you know how to use it; most people waste it through inattention."
  argumentative_structure: "dialectical"
```

---

## Fiction: Scene Beat Extraction

**CRITICAL FOR FICTION:** For fiction, extract KEY STORY MOMENTS (scenes where things happen), not quotable metaphors. This is the primary content source for image generation in fiction.

### Scene Beat Structure

```yaml
scene_beats:
  - beat_id: string
    scene_description: string  # What happens (action, not atmosphere)
    characters_present: [string]
    location: string
    story_function: "hook" | "setup" | "complication" | "revelation" | "confrontation" | "climax" | "resolution"
    key_dialogue: string | null  # Most important line if dialogue scene
    source_paragraphs: [int]
```

### Extraction Priority for Fiction

1. **Actions** - Characters doing things (entering, speaking, fighting)
2. **Confrontations** - Characters in conflict or tension
3. **Revelations** - Information discovered or revealed
4. **Turning points** - Plot pivots
5. **Character moments** - Defining behavior or decision

### DO NOT Extract as Scene Beats

- Similes/metaphors (these are STYLE, not content)
- Pure atmospheric description (use for mood, not subject)
- Internal monologue without action

### Distinguishing Literal vs Figurative Content

When extracting scene beats, identify what ACTUALLY HAPPENS vs what is DESCRIPTIVE LANGUAGE:

| Text | Type | Visualization |
|------|------|---------------|
| "The door opened" | LITERAL | Visualize the door opening |
| "like a dead moth" | FIGURATIVE | Do NOT visualize a moth |
| "She sat on the edge of the chair" | LITERAL | Visualize her sitting |
| "The city coughed and wheezed" | FIGURATIVE | City cannot literally cough |
| "He fired the gun" | LITERAL | Visualize the gunshot |
| "blood went cold" | FIGURATIVE | Do NOT visualize frozen blood |

### Example - WRONG Extraction

```yaml
# BAD: Extracts simile as content
text: "The name dropped onto my desk like a dead moth"
image_subject: "A dead moth on a desk"
```

This is wrong because "like a dead moth" is a SIMILE describing HOW the name landed, not WHAT happened.

### Example - CORRECT Extraction

```yaml
# GOOD: Extracts the actual scene
scene_beats:
  - beat_id: "sb_001"
    scene_description: "Nervous young woman enters detective's office, says 'Van Helsing?'"
    characters_present: ["Mina Harker", "Mallory (narrator)"]
    location: "Mallory's shabby office"
    story_function: "hook"
    key_dialogue: "'Van Helsing?' The name dropped onto my desk like a dead moth."
    source_paragraphs: [1, 2]
```

The simile informs MOOD and STYLE, but the CONTENT is: a woman visits and asks about Van Helsing.

### Scene Beat Examples by Story Function

| Function | Example Scene |
|----------|--------------|
| hook | "Mina Harker enters the detective's shabby office, nervously asks about Van Helsing" |
| setup | "Mina explains the vampire situation, hands over a foreign letter" |
| complication | "At the pier, the old man's ship arrives in the fog" |
| revelation | "Van Helsing opens his case, revealing stakes, crosses, and ancient texts" |
| confrontation | "Mallory fires point-blank; the Count doesn't flinch" |
| climax | "Van Helsing presses the crucifix to the Count's hand; smoke rises" |
| resolution | "The three stand in the dark office, processing what just happened" |

---

## Fiction: Character Canon (Identity Locks)

**FICTION ONLY.** In addition to scene beats, emit `character_canon`: one canonical visual description per recurring character (any character appearing in 2+ scene beats, plus protagonist and antagonist). Downstream tasks embed these descriptions verbatim into every image prompt featuring the character, so faces, hair, builds, and costumes stay identical across all slides.

### Character Canon Structure

```yaml
character_canon:
  - name: string                 # Canonical name — reused verbatim downstream
    age: string                  # e.g. "late 30s"
    face: string                 # Facial features, eyes, complexion
    hair: string                 # Color, length, style
    build: string                # Height/physique
    costume: string              # Typical clothing across the story
    distinguishing: string | null  # Scars, jewelry, props, distinctive wear
```

### Rules

- Derive details from the source text. Where the text is silent, INVENT one concrete, era- and genre-appropriate detail and keep it stable — vagueness ("average build") causes per-slide re-rolls of the character's look.
- Use the exact same name strings as `characters_present` in scene_beats.
- Write compact phrases, not sentences: "gaunt, sharp cheekbones, hooded grey eyes".
- Omit `character_canon` entirely for non-fiction genres.

### Example

```yaml
character_canon:
  - name: "Mina Harker"
    age: "mid 20s"
    face: "pale oval face, dark anxious eyes, thin brows"
    hair: "dark brown, pinned back, loose strands at the temples"
    build: "slight, narrow shoulders"
    costume: "grey wool traveling coat over a high-collared white blouse"
    distinguishing: "small silver crucifix on a neck chain"
  - name: "Mallory"
    age: "early 40s"
    face: "weathered, heavy jaw, tired grey eyes"
    hair: "short dark hair, greying at the temples"
    build: "broad-shouldered, slight stoop"
    costume: "rumpled brown suit, loosened tie, shoulder holster"
    distinguishing: "old scar through the left eyebrow"
```

---

## Section Function Definitions

| Function | Description | Typical Position |
|----------|-------------|------------------|
| introduction | Sets stage, establishes stakes | Opening |
| body | Develops argument or narrative | Middle |
| transition | Bridges major sections | Between body sections |
| conclusion | Resolves, calls to action | Ending |

---

## Quotable Passage Quality Matrix

| Quality | Definition | Example |
|---------|------------|---------|
| standalone | Works without surrounding context | "The ink dries in seconds; the concrete takes a season." |
| aphoristic | Pithy, memorable, quotable | "Maps are useful. Rivers are what they describe." |
| visualizable | Creates clear mental image | "wrapped themselves in cellophane" |
| emotional_punch | Evokes strong feeling | "We were not optimizing for truth. We were optimizing for forgiveness." |
| conceptual | Defines or explains clearly | "our collective capacity to live somewhere is our Stock" |

---

## Metaphor Inventory Guidelines

### Dominant Metaphor Detection

A dominant metaphor is present when:
- Same conceptual frame appears 3+ times
- Multiple related terms form a system
- Metaphor structures the entire argument

**Extended metaphor example (policy):**
- Frame: Water infrastructure
- Components: cistern, valve, inflows, pressure, flow
- System: Economics as plumbing

**Unified metaphor example (analytical):**
- Frame: Map vs. River
- Components: map (static), river (dynamic)
- System: Standard vs. AI as navigation dichotomy

**Distributed metaphor example (personal):**
- No single frame dominates
- Multiple independent metaphors per section
- Each slide can have unique visual

### Secondary Metaphor Tracking

Note whether each secondary metaphor:
- Extends the dominant metaphor (same domain)
- Contrasts with dominant metaphor
- Stands alone (distributed strategy)

---

## Emotional Arc Mapping

### Energy Levels (1-5)

| Level | Description | Indicators |
|-------|-------------|------------|
| 1 | Quiet, reflective | Contemplation, setting scene |
| 2 | Building | Introduction of tension |
| 3 | Moderate intensity | Active development |
| 4 | High intensity | Climactic moments, revelations |
| 5 | Peak | Maximum emotional/argumentative force |

### Resolution Types

| Type | Description | Genre Affinity |
|------|-------------|----------------|
| personal | Individual action or stance | Personal essay |
| imperative | Call to action for audience | Analytical critique |
| hopeful | Future-oriented optimism | Policy argument |
| open | Question or uncertainty | Any |

---

## Example Output (Policy Argument)

```yaml
structural_analysis:
  sections:
    - id: "intro"
      title: null
      paragraph_start: 1
      paragraph_end: 2
      function: "introduction"
    - id: "cistern"
      title: "The Cistern and the Valve"
      paragraph_start: 3
      paragraph_end: 5
      function: "body"
    - id: "vetocracy"
      title: null
      paragraph_start: 6
      paragraph_end: 7
      function: "body"
    - id: "reframe"
      title: null
      paragraph_start: 8
      paragraph_end: 9
      function: "transition"
    - id: "digital"
      title: null
      paragraph_start: 10
      paragraph_end: 12
      function: "body"
    - id: "resolution"
      title: null
      paragraph_start: 13
      paragraph_end: 14
      function: "conclusion"

quotable_passages:
  - id: "q1"
    text: "The ink on the check dries in seconds; the concrete in a foundation takes a season."
    source_paragraph: 2
    qualities:
      standalone: true
      aphoristic: true
      visualizable: true
      emotional_punch: true
      conceptual: true
    suggested_usage: "callout"
  - id: "q2"
    text: "We are subsidizing the demand for a life we refuse to actually build."
    source_paragraph: 4
    qualities:
      standalone: true
      aphoristic: true
      visualizable: false
      emotional_punch: true
      conceptual: true
    suggested_usage: "headline"
  - id: "q3"
    text: "A young couple sits in a coffee shop, scrolling listings on a phone, radiating the quiet static of a stuck world."
    source_paragraph: 1
    qualities:
      standalone: true
      aphoristic: false
      visualizable: true
      emotional_punch: true
      conceptual: false
    suggested_usage: "body"

metaphor_inventory:
  dominant_metaphor:
    present: true
    description: "Water infrastructure as economic system"
    components: ["cistern", "valve", "inflows", "pressure", "flow", "trickle"]
    source_paragraphs: [3, 4, 5, 8]
  secondary_metaphors:
    - concept: "policy as check-writing"
      visual: "ink drying on check"
      source_paragraph: 2
      extends_dominant: false
    - concept: "stagnation as ice"
      visual: "frozen, cracking ice"
      source_paragraph: 13
      extends_dominant: true
    - concept: "obstruction as valve"
      visual: "hand on valve wheel"
      source_paragraph: 6
      extends_dominant: true

emotional_arc:
  opening_energy: 3
  trajectory: [3, 4, 4, 4, 5, 4, 4, 5, 4, 3]
  peak_moments: [7, 12]
  nadir_moment: null
  resolution_type: "hopeful"

key_concepts:
  - concept: "stock vs. flow"
    importance: "primary"
    visualizable: true
    first_mention: 3
  - concept: "lag-time"
    importance: "primary"
    visualizable: true
    first_mention: 7
  - concept: "vetocracy"
    importance: "secondary"
    visualizable: true
    first_mention: 6
  - concept: "induced demand"
    importance: "primary"
    visualizable: true
    first_mention: 8
```

---

## Validation Checklist

Before submitting output, verify:

- [ ] Section ranges cover all paragraphs in order, without gaps or overlaps
- [ ] At least 5 quotable passages identified
- [ ] Dominant metaphor presence correctly determined
- [ ] Emotional arc trajectory matches section count
- [ ] Peak moments are paragraph IDs that exist
- [ ] Each key concept has visualizable assessment
- [ ] **Fiction:** every recurring character (2+ scene beats), plus protagonist and antagonist, has a `character_canon` entry whose name matches `characters_present` exactly
