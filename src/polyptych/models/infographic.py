"""Pydantic models for the infographic pipeline (Tasks I0-I2)."""

from typing import Literal
from pydantic import BaseModel, Field

from .slide import GenerationNotes


# =============================================================================
# Task I0: Content Analysis (Infographic Pipeline)
# =============================================================================


class InfographicKeyPoint(BaseModel):
    """A key point extracted from the source content."""

    id: str = Field(..., description="Unique identifier (e.g., 'KP1', 'KP2')")
    statement: str = Field(..., description="Concise statement of the key point")
    importance: Literal["primary", "secondary", "supporting"] = Field(
        ..., description="Importance level for the infographic"
    )
    source_paragraphs: list[int] = Field(
        ..., description="Paragraph numbers where this point is discussed"
    )


class InfographicRelationship(BaseModel):
    """A relationship between two key points."""

    from_point: str = Field(..., description="ID of the source key point")
    to_point: str = Field(..., description="ID of the target key point")
    relationship_type: Literal[
        "causes", "supports", "contradicts", "precedes", "contains", "compares_to"
    ] = Field(..., description="Type of relationship")
    label: str = Field(..., description="Short label describing the relationship")


class VisualizableData(BaseModel):
    """A piece of data that can be visualized in the infographic."""

    description: str = Field(..., description="What this data represents")
    data_type: Literal[
        "comparison", "progression", "hierarchy", "cycle", "distribution", "timeline"
    ] = Field(..., description="Type of data visualization suitable")
    values: list[str] = Field(
        ..., description="Key values or labels for the visualization"
    )


class ContentStructure(BaseModel):
    """The structural pattern identified in the content."""

    primary_pattern: Literal[
        "argument", "comparison", "process", "hierarchy", "timeline", "problem_solution"
    ] = Field(..., description="Primary structural pattern of the content")
    rationale: str = Field(..., description="Why this pattern fits the content")
    section_count: int = Field(
        ..., description="Recommended number of major sections (3-6)"
    )


class TaskI0Output(BaseModel):
    """Output from Task I0: Content Analysis for Infographic."""

    title: str = Field(..., description="Proposed infographic title")
    subtitle: str = Field(..., description="Proposed subtitle or tagline")
    thesis: str = Field(..., description="Core thesis or central message")
    key_points: list[InfographicKeyPoint] = Field(
        ..., description="Key points extracted from the content"
    )
    relationships: list[InfographicRelationship] = Field(
        ..., description="Relationships between key points"
    )
    visualizable_data: list[VisualizableData] = Field(
        ..., description="Data elements suitable for visualization"
    )
    content_structure: ContentStructure = Field(
        ..., description="Identified structural pattern and section recommendation"
    )
    tone: str = Field(..., description="Overall tone of the content")
    target_audience: str = Field(..., description="Inferred target audience")


# =============================================================================
# Task I1: Design Specification (Infographic Pipeline)
# =============================================================================


class InfographicSection(BaseModel):
    """A section of the infographic layout."""

    title: str = Field(..., description="Section title")
    content_summary: str = Field(..., description="What this section covers")
    visual_element: Literal[
        "flowchart",
        "hub_spoke",
        "comparison_grid",
        "timeline",
        "statistics",
        "icon_list",
        "process_steps",
        "pyramid",
        "venn_diagram",
        "bar_chart",
        "pie_chart",
        "matrix",
    ] = Field(..., description="Type of visual element for this section")
    visual_description: str = Field(
        ..., description="Detailed description of the visual element"
    )
    placement: Literal[
        "top_left",
        "top_center",
        "top_right",
        "middle_left",
        "center",
        "middle_right",
        "bottom_left",
        "bottom_center",
        "bottom_right",
        "full_width_top",
        "full_width_middle",
        "full_width_bottom",
        "left_half",
        "right_half",
    ] = Field(..., description="Placement within the infographic layout")


class InfographicColorPalette(BaseModel):
    """Color palette for the infographic."""

    primary: str = Field(..., description="Primary color (hex)")
    secondary: str = Field(..., description="Secondary color (hex)")
    accent: str = Field(..., description="Accent color (hex)")
    background: str = Field(..., description="Background color (hex)")
    text: str = Field(..., description="Text color (hex)")
    rationale: str = Field(..., description="Why these colors suit the content")


class TaskI1Output(BaseModel):
    """Output from Task I1: Design Specification for Infographic."""

    layout_type: Literal[
        "vertical_flow",
        "modular_grid",
        "hub_spoke",
        "timeline",
        "comparison",
        "process",
        "mixed",
    ] = Field(..., description="Overall layout pattern")
    orientation: Literal["landscape", "portrait"] = Field(
        ..., description="Image orientation"
    )
    sections: list[InfographicSection] = Field(
        ..., description="Sections of the infographic"
    )
    color_palette: InfographicColorPalette = Field(
        ..., description="Color palette specification"
    )
    typography_notes: str = Field(
        ..., description="Typography guidance (font style, hierarchy, weight)"
    )
    visual_style: Literal[
        "semi_flat",
        "isometric",
        "minimalist",
        "illustrated",
        "corporate",
        "editorial",
        "hand_drawn",
    ] = Field(..., description="Visual illustration style")
    icon_style: Literal["line", "filled", "duotone", "outline", "glyph"] = Field(
        ..., description="Icon rendering style"
    )
    title_treatment: str = Field(
        ..., description="How the title should be visually treated"
    )
    flow_description: str = Field(
        ..., description="How the viewer's eye should move through the infographic"
    )


# =============================================================================
# Task I2: Image Prompt Generation (Infographic Pipeline)
# =============================================================================


class InfographicVariant(BaseModel):
    """A single infographic prompt variant."""

    variant_number: int = Field(
        ..., description="Sequential variant number (1-indexed)"
    )
    interpretation: str = Field(
        ..., description="Brief description of this variant's creative angle"
    )
    full_prompt: str = Field(
        ..., description="Complete image generation prompt for this infographic"
    )
    generation_notes: GenerationNotes = Field(
        ..., description="Image generation configuration"
    )


class TaskI2Output(BaseModel):
    """Output from Task I2: Image Prompt Generation for Infographic."""

    variants: list[InfographicVariant] = Field(
        ..., description="Prompt variants for the infographic"
    )


class I2PromptIssue(BaseModel):
    """A quality issue found in a single infographic prompt variant."""

    variant_number: int = Field(
        ..., description="Variant number where the issue was found"
    )
    issue_type: Literal[
        "color_inconsistency",
        "semantic_loss",
        "coverage_gap",
        "flow_mismatch",
        "text_density",
        "style_drift",
        "vague_or_overloaded",
    ] = Field(..., description="Category of the issue")
    description: str = Field(..., description="What is wrong and why it matters")
    severity: Literal["critical", "important", "minor"] = Field(
        ..., description="How urgent the fix is"
    )
    suggested_fix: str = Field(..., description="Concrete suggestion for correction")


class TaskI2Critique(BaseModel):
    """Output from I2 Critique: Infographic prompt audit.

    Audits each i2 prompt variant against the i0 content analysis (coverage),
    the i1 design specification (entity consistency, flow), and the rendering
    quality tier (text density) before the expensive image-generation step.
    """

    prompt_issues: list[I2PromptIssue] = Field(
        default_factory=list,
        description="Per-variant prompt quality issues",
    )
    dropped_key_content: list[str] = Field(
        default_factory=list,
        description=(
            "Primary key points or striking visualizable data from i0 that no "
            "longer appear in the prompt (informational; only an issue when "
            "also flagged as a coverage_gap)"
        ),
    )
    overall_assessment: str = Field(
        ..., description="Summary of prompt quality and priority fixes"
    )
