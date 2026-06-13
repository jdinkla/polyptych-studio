"""Pydantic models for the slide generation pipeline (Tasks 1-7)."""

from typing import Literal
from pydantic import BaseModel, Field, model_validator


# =============================================================================
# Task 1: Genre Classification
# =============================================================================


class GenreParameters(BaseModel):
    """Parameters derived from genre classification."""

    compression_ratio: float
    structure_type: Literal[
        "3-act emotional",
        "4-part argument",
        "5-part policy",
        "narrative_arc",
        "strategic_diagnostic",
        "meditative_spiral",
        "dialectical_argument",
    ]
    metaphor_strategy: Literal["distributed", "unified", "extended"]
    color_system: Literal[
        "varied",
        "strict_dichotomy",
        "dual_accent",
        "mood_based",
        "evidence_accent",
        "conceptual_accent",
    ]
    closing_strategy: Literal[
        "personal_action", "imperative", "human_return", "resolution"
    ]


class SignalDetected(BaseModel):
    """A signal detected during genre classification."""

    signal_name: str
    evidence: str


class Task1Output(BaseModel):
    """Output from Task 1: Genre Classification."""

    genre: Literal[
        "personal_essay",
        "analytical_critique",
        "policy_argument",
        "fiction",
        "strategic_diagnostic",
        "conceptual_essay",
    ]
    confidence: float = Field(ge=0, le=1)
    parameters: GenreParameters
    signals_detected: list[SignalDetected]


# =============================================================================
# Task 2: Source Analysis
# =============================================================================


class SectionAnalysis(BaseModel):
    """Analysis of a section in the source essay.

    Paragraph membership is a contiguous 1-indexed inclusive range
    (``paragraph_start``..``paragraph_end``) — an exhaustive int list was
    token-wasteful and invited off-by-one errors for long sources. Legacy
    outputs with a ``paragraphs`` list are migrated on load (min..max).
    ``word_count`` is computed in post-processing from the source text, not
    requested from the model.
    """

    id: str
    title: str | None = None
    paragraph_start: int
    paragraph_end: int
    function: Literal["introduction", "body", "conclusion", "transition"]
    word_count: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_paragraphs(cls, data: object) -> object:
        if (
            isinstance(data, dict)
            and "paragraph_start" not in data
            and data.get("paragraphs")
        ):
            data = dict(data)
            plist = data.pop("paragraphs")
            data["paragraph_start"] = min(plist)
            data["paragraph_end"] = max(plist)
        return data

    @model_validator(mode="after")
    def _check_range(self) -> "SectionAnalysis":
        if self.paragraph_end < self.paragraph_start:
            raise ValueError(
                f"paragraph_end ({self.paragraph_end}) must be >= "
                f"paragraph_start ({self.paragraph_start})"
            )
        return self

    @property
    def paragraphs(self) -> list[int]:
        """Inclusive list view of the paragraph range (consumer interface)."""
        return list(range(self.paragraph_start, self.paragraph_end + 1))


class QuotablePassageQualities(BaseModel):
    """Quality markers for a quotable passage."""

    standalone: bool
    aphoristic: bool
    visualizable: bool
    emotional_punch: bool
    conceptual: bool


class QuotablePassage(BaseModel):
    """A quotable passage extracted from the source."""

    id: str
    text: str
    source_paragraph: int
    qualities: QuotablePassageQualities
    suggested_usage: Literal["headline", "body", "callout", "closing"]


class DominantMetaphor(BaseModel):
    """The dominant metaphor in the source essay."""

    present: bool
    description: str
    components: list[str]
    source_paragraphs: list[int]


class SecondaryMetaphor(BaseModel):
    """A secondary metaphor in the source essay."""

    concept: str
    visual: str
    source_paragraph: int
    extends_dominant: bool


class MetaphorInventory(BaseModel):
    """Inventory of metaphors in the source essay."""

    dominant_metaphor: DominantMetaphor
    secondary_metaphors: list[SecondaryMetaphor]


class EmotionalArc(BaseModel):
    """Emotional arc analysis of the source essay."""

    opening_energy: int = Field(ge=1, le=5)
    trajectory: list[int]
    peak_moments: list[int]
    nadir_moment: int | None = None
    resolution_type: Literal["personal", "imperative", "hopeful", "open"]


class KeyConcept(BaseModel):
    """A key concept identified in the source essay."""

    concept: str
    importance: Literal["primary", "secondary"]
    visualizable: bool
    first_mention: int


class ConceptDistinction(BaseModel):
    """A distinction between two terms in a conceptual essay."""

    term_a: str
    term_b: str
    basis: str


class ConceptRelation(BaseModel):
    """A relationship between two concepts."""

    from_concept: str
    to_concept: str
    relation: Literal[
        "supports",
        "contradicts",
        "refines",
        "exemplifies",
        "contains",
        "precondition_for",
    ]


class RichConcept(BaseModel):
    """A richly typed concept for conceptual essay analysis."""

    concept: str
    concept_type: Literal[
        "claim", "framework", "definition", "taxonomy", "mental_model", "distinction"
    ]
    importance: Literal["primary", "secondary"]
    visualizable: bool
    source_paragraphs: list[int]
    distinction: ConceptDistinction | None = None
    summary: str


class ConceptArchitecture(BaseModel):
    """Full concept architecture for a conceptual essay."""

    concepts: list[RichConcept]
    relations: list[ConceptRelation]
    central_claim: str
    argumentative_structure: Literal["linear", "dialectical", "taxonomic", "spiral"]


class StructuralAnalysis(BaseModel):
    """Structural analysis of the source essay."""

    sections: list[SectionAnalysis]


class SceneBeat(BaseModel):
    """A key story moment extracted from fiction."""

    beat_id: str
    scene_description: str
    characters_present: list[str]
    location: str
    story_function: Literal[
        "hook",
        "setup",
        "complication",
        "revelation",
        "confrontation",
        "climax",
        "resolution",
    ]
    key_dialogue: str | None = None
    source_paragraphs: list[int]


class CharacterSheet(BaseModel):
    """Canonical visual description of a recurring fiction character.

    Produced by task2 for fiction sources only; consumed by task6 (canonical
    names in ``characters_in_frame``) and task7 (verbatim identity locks) so a
    character's face, build, and costume stay identical across slides.
    """

    name: str  # Canonical name, used verbatim in characters_in_frame
    age: str  # e.g. "late 30s"
    face: str  # Facial features incl. eyes, complexion
    hair: str  # Color, length, style
    build: str  # Height/physique
    costume: str  # Typical clothing across the story
    distinguishing: str | None = None  # Scars, jewelry, props, distinctive wear

    def identity_lock_line(self) -> str:
        """Render the single canonical description line embedded in prompts.

        Deterministic so every slide carries the exact same string.
        """
        parts = [self.age, self.face, self.hair, self.build, self.costume]
        if self.distinguishing:
            parts.append(self.distinguishing)
        return f"{self.name}: " + "; ".join(parts)


class Task2Output(BaseModel):
    """Output from Task 2: Source Analysis."""

    structural_analysis: StructuralAnalysis
    quotable_passages: list[QuotablePassage]  # For essays
    scene_beats: list[SceneBeat] | None = None  # For fiction - key story moments
    character_canon: list[CharacterSheet] | None = None  # For fiction - identity locks
    metaphor_inventory: MetaphorInventory
    emotional_arc: EmotionalArc
    key_concepts: list[KeyConcept]
    concept_architecture: ConceptArchitecture | None = None  # For conceptual_essay


# =============================================================================
# Task 3: Structure Planning
# =============================================================================


class SlideSequenceItem(BaseModel):
    """A single slide in the planned sequence."""

    slide_number: int
    role: str
    source_section: str
    intensity: int = Field(ge=1, le=5)
    notes: str


class ArcVisualization(BaseModel):
    """Visualization of the presentation arc."""

    type: Literal["3-act", "4-part", "5-part", "narrative", "meditative", "dialectical"]
    peaks: list[int]
    nadir: int | None = None
    concession: int | None = None


class Task3Output(BaseModel):
    """Output from Task 3: Structure Planning."""

    slide_count: int
    slide_sequence: list[SlideSequenceItem]
    arc_visualization: ArcVisualization


# =============================================================================
# Task 4: Content Allocation
# =============================================================================


class HeadlineContent(BaseModel):
    """Headline content for a slide."""

    text: str
    source: Literal["direct", "synthesized", "dramatized"]
    source_paragraph: int | None = None


class SubheadlineContent(BaseModel):
    """Subheadline content for a slide."""

    text: str | None = None
    source_paragraph: int | None = None


class BodyTextContent(BaseModel):
    """Body text content for a slide."""

    summary: str
    source_paragraphs: list[int]
    # Compression factor source_words / summary_words. Computed in
    # post-processing (run_task_04) — the model cannot count words reliably
    # and used to fabricate this. None when summary or sources are empty.
    compression_applied: float | None = None
    original_text_start: str | None = None


class QuoteContent(BaseModel):
    """Quote content for a slide."""

    text: str | None = None
    source_paragraph: int | None = None


class SlideAllocation(BaseModel):
    """Content allocation for a single slide."""

    slide_number: int
    headline: HeadlineContent
    subheadline: SubheadlineContent | None = None
    body_text: BodyTextContent
    quote: QuoteContent | None = None
    key_metaphor: str | None = None  # For essays - the metaphor to visualize
    scene_beat_id: str | None = None  # For fiction - reference to Task 2 scene beat
    labels: list[str] | None = None


class Task4Output(BaseModel):
    """Output from Task 4: Content Allocation."""

    allocations: list[SlideAllocation]


# =============================================================================
# Task 5: Visual Design Specification
# =============================================================================


class BackgroundSpec(BaseModel):
    """Background specification."""

    color: str  # hex color
    texture: str


class HeadlineTypography(BaseModel):
    """Headline typography specification."""

    family: Literal["serif", "sans-serif", "monospace"]
    weight: str
    style: Literal["title_case", "all_caps", "mixed"]


class BodyTypography(BaseModel):
    """Body typography specification."""

    family: str
    size: str


class QuoteTypography(BaseModel):
    """Quote typography specification."""

    family: str
    style: Literal["italic", "bold", "regular"]


class Typography(BaseModel):
    """Typography specification."""

    headline: HeadlineTypography
    body: BodyTypography
    quote: QuoteTypography


class ColorSymbol(BaseModel):
    """Color symbolism mapping."""

    color: str  # hex color
    meaning: str


class ColorPalette(BaseModel):
    """Color palette specification."""

    primary_accent: str = Field(..., description="Hex color for primary accent")
    secondary_accent: str = Field(..., description="Hex color for secondary accent")
    allow_override: bool = Field(
        default=False, description="Allow per-slide color variation"
    )
    symbolism: list[ColorSymbol]


class Motif(BaseModel):
    """Visual motif specification."""

    type: Literal["unified", "distributed", "extended"]
    primary_visual: str = Field(..., description="Primary visual motif description")
    fallback_elements: list[str] | None = Field(
        default=None, description="Fallback visual elements when primary not applicable"
    )
    components: list[str] | None = None
    persistence: float = Field(ge=0, le=1)


class EnvironmentalMotif(BaseModel):
    """Persistent atmospheric element across slides (e.g., shoji shadows, rain)."""

    element: str
    treatment: str
    persistence: float = Field(ge=0, le=1)
    source_inspiration: str | None = None


class LayoutPreferences(BaseModel):
    """Layout preferences specification."""

    diagram_heavy: bool
    comparison_percentage: float
    preferred_patterns: list[str]


class VisualStyle(BaseModel):
    """Visual style consistency specification."""

    primary: str = Field(
        ..., description="Primary visual style (e.g., 'photorealistic', 'watercolor')"
    )
    secondary: str | None = Field(
        default=None,
        description="Secondary style for accent slides (e.g., opening/closing)",
    )
    forbidden: list[str] = Field(
        default_factory=list, description="Styles that should never be used"
    )
    transition_rule: str = Field(
        default="Secondary style only at act boundaries",
        description="Rule for when secondary style is allowed",
    )


class SpecialTechnique(BaseModel):
    """Special design technique."""

    technique: str
    when_to_use: str
    # How the technique renders visually (e.g. the callout treatment spec
    # that task7 bakes into text_elements). The task5 prompt has always
    # requested this key; without the field it was silently dropped.
    visual_spec: str | None = None


class DesignSystem(BaseModel):
    """Complete design system specification."""

    background: BackgroundSpec
    typography: Typography
    color_palette: ColorPalette
    motif: Motif
    visual_style: VisualStyle = Field(..., description="Visual style consistency rules")
    environmental_motif: EnvironmentalMotif | None = Field(
        default=None, description="Persistent atmospheric element across slides"
    )
    layout_preferences: LayoutPreferences
    special_techniques: list[SpecialTechnique]


class Task5Output(BaseModel):
    """Output from Task 5: Visual Design Specification."""

    design_system: DesignSystem


# =============================================================================
# Task 6: Slide Specification
# =============================================================================


class SlideContent(BaseModel):
    """Content for a single slide."""

    headline: str
    subheadline: str | None = None
    body_text: str | None = None
    quote: str | None = None
    callout: str | None = Field(
        default=None, description="Pull-quote with distinct visual treatment"
    )
    labels: list[str] | None = None


class SlideLayout(BaseModel):
    """Layout specification for a slide."""

    pattern: str
    grid_description: str


class ImageSpec(BaseModel):
    """Image specification for a slide."""

    subject: str
    mood: str
    color_temperature: str
    metaphor_visualized: str | None = None  # For essays - the metaphor being visualized
    scene_visualized: str | None = None  # For fiction - what's happening in the scene
    characters_in_frame: list[str] | None = None  # For fiction - who is visible
    camera_angle: str | None = None  # For fiction - wide, medium, close-up, POV
    key_action: str | None = None  # For fiction - the moment being captured
    style_notes: str


class ColorUsage(BaseModel):
    """Color usage for a slide."""

    background: str  # hex color
    accents_used: list[str]  # hex colors


class SlideVisual(BaseModel):
    """Visual specification for a slide."""

    image_spec: ImageSpec
    color_usage: ColorUsage
    typography_notes: str


class ArcPosition(BaseModel):
    """Arc position for a slide."""

    intensity: int = Field(ge=1, le=5)
    function: str
    transition_to_next: str


class SlideSpec(BaseModel):
    """Complete specification for a single slide."""

    number: int
    role: str
    content: SlideContent
    layout: SlideLayout
    visual: SlideVisual
    arc_position: ArcPosition


class Task6Output(BaseModel):
    """Output from Task 6: Slide Specification."""

    slides: list[SlideSpec]


# =============================================================================
# Task 7: Image Prompt Generation
# =============================================================================


class ImagePromptSections(BaseModel):
    """Individual sections of the Nano-Banana Pro prompt."""

    goal: str
    subject: str
    composition: str
    spatial_relationships: str | None = None
    setting: str
    lighting: str
    text_elements: str | None = None
    style: str
    fidelity: str
    consistency: str


class GenerationNotes(BaseModel):
    """Generation configuration notes."""

    aspect_ratio: Literal["16:9", "4:3", "1:1"]
    negative_prompts: list[str] | None = None
    key_requirements: list[str]


class ImagePrompt(BaseModel):
    """Complete image prompt structure."""

    full_prompt: str
    sections: ImagePromptSections | None = None
    generation_notes: GenerationNotes


class SlideImagePrompt(BaseModel):
    """Image prompt for a single slide."""

    slide_number: int
    image_prompt: ImagePrompt


class ImagePromptDraft(BaseModel):
    """LLM-generated portion of an image prompt — no ``full_prompt``.

    Task7's structured-output schema: the model writes ``sections`` and
    ``generation_notes`` once; code assembles ``full_prompt``
    deterministically (``tasks.task_07_prompts.assemble_full_prompt``) and
    injects the pre-computed text elements. This halves the output tokens of
    the most expensive text task and removes drift between the two
    representations. ``text_elements`` inside sections is overwritten by code.
    """

    sections: ImagePromptSections
    generation_notes: GenerationNotes


class SlideImagePromptDraft(BaseModel):
    """Draft image prompt for a single slide (LLM output)."""

    slide_number: int
    image_prompt: ImagePromptDraft


class Task7Draft(BaseModel):
    """LLM response schema for task7 — converted to :class:`Task7Output`."""

    slide_prompts: list[SlideImagePromptDraft]


class Task7Output(BaseModel):
    """Output from Task 7: Image Prompt Generation."""

    slide_prompts: list[SlideImagePrompt]
    # Image provider whose best-practice guidelines were baked into the
    # prompts (prompts/providers/<provider>-best-practices.md). Stamped by
    # pipeline code after generation — never trusted from the LLM. None for
    # output dirs that predate provider recording.
    prompt_provider: str | None = None
