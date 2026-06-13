"""Factory functions for slide pipeline Pydantic models (Task1 - Task7).

Mirrors tests/polyptych/anime/factories.py. All factories return valid model
instances with sensible defaults that can be overridden via keyword arguments.
"""

from __future__ import annotations

from polyptych.models import (
    ArcPosition,
    ArcVisualization,
    BackgroundSpec,
    BodyTextContent,
    BodyTypography,
    ColorPalette,
    ColorSymbol,
    ColorUsage,
    DesignSystem,
    DominantMetaphor,
    EmotionalArc,
    GenerationNotes,
    GenreParameters,
    HeadlineContent,
    HeadlineTypography,
    ImagePrompt,
    ImagePromptSections,
    ImageSpec,
    KeyConcept,
    LayoutPreferences,
    MetaphorInventory,
    Motif,
    QuotablePassage,
    QuotablePassageQualities,
    QuoteTypography,
    SectionAnalysis,
    SignalDetected,
    SlideAllocation,
    SlideContent,
    SlideImagePrompt,
    SlideLayout,
    SlideSequenceItem,
    SlideSpec,
    SlideVisual,
    SpecialTechnique,
    StructuralAnalysis,
    Task1Output,
    Task2Output,
    Task3Output,
    Task4Output,
    Task5Output,
    Task6Output,
    Task7Output,
    Typography,
    VisualStyle,
)


# =============================================================================
# Task 1: Genre Classification
# =============================================================================


def make_task1_output(
    genre: str = "personal_essay",
    **overrides,
) -> Task1Output:
    defaults = dict(
        genre=genre,
        confidence=0.9,
        parameters=GenreParameters(
            compression_ratio=0.5,
            structure_type="3-act emotional",
            metaphor_strategy="distributed",
            color_system="varied",
            closing_strategy="personal_action",
        ),
        signals_detected=[
            SignalDetected(signal_name="first_person", evidence="uses 'I' throughout"),
        ],
    )
    defaults.update(overrides)
    return Task1Output(**defaults)


# =============================================================================
# Task 2: Source Analysis
# =============================================================================


def make_task2_output(**overrides) -> Task2Output:
    defaults = dict(
        structural_analysis=StructuralAnalysis(
            sections=[
                SectionAnalysis(
                    id="s1",
                    title="Opening",
                    paragraph_start=1,
                    paragraph_end=2,
                    function="introduction",
                    word_count=120,
                ),
                SectionAnalysis(
                    id="s2",
                    title="Body",
                    paragraph_start=3,
                    paragraph_end=4,
                    function="body",
                    word_count=200,
                ),
                SectionAnalysis(
                    id="s3",
                    title="Close",
                    paragraph_start=5,
                    paragraph_end=5,
                    function="conclusion",
                    word_count=80,
                ),
            ],
        ),
        quotable_passages=[
            QuotablePassage(
                id="q1",
                text="The clock struck midnight.",
                source_paragraph=5,
                qualities=QuotablePassageQualities(
                    standalone=True,
                    aphoristic=False,
                    visualizable=True,
                    emotional_punch=True,
                    conceptual=False,
                ),
                suggested_usage="closing",
            ),
        ],
        metaphor_inventory=MetaphorInventory(
            dominant_metaphor=DominantMetaphor(
                present=True,
                description="Rain as uncertainty",
                components=["rain", "window"],
                source_paragraphs=[1],
            ),
            secondary_metaphors=[],
        ),
        emotional_arc=EmotionalArc(
            opening_energy=2,
            trajectory=[2, 3, 4, 4, 5],
            peak_moments=[5],
            nadir_moment=None,
            resolution_type="open",
        ),
        key_concepts=[
            KeyConcept(
                concept="isolation",
                importance="primary",
                visualizable=True,
                first_mention=1,
            ),
        ],
    )
    defaults.update(overrides)
    return Task2Output(**defaults)


# =============================================================================
# Task 3: Structure Planning
# =============================================================================


def make_task3_output(slide_count: int = 3, **overrides) -> Task3Output:
    defaults = dict(
        slide_count=slide_count,
        slide_sequence=[
            SlideSequenceItem(
                slide_number=i,
                role="opening" if i == 1 else ("closing" if i == slide_count else "body"),
                source_section=f"s{min(i, 3)}",
                intensity=min(5, i + 1),
                notes=f"Slide {i} notes",
            )
            for i in range(1, slide_count + 1)
        ],
        arc_visualization=ArcVisualization(
            type="3-act",
            peaks=[slide_count],
            nadir=None,
            concession=None,
        ),
    )
    defaults.update(overrides)
    return Task3Output(**defaults)


# =============================================================================
# Task 4: Content Allocation
# =============================================================================


def make_task4_output(slide_count: int = 3, **overrides) -> Task4Output:
    defaults = dict(
        allocations=[
            SlideAllocation(
                slide_number=i,
                headline=HeadlineContent(
                    text=f"Slide {i} Headline",
                    source="synthesized",
                    source_paragraph=i,
                ),
                subheadline=None,
                body_text=BodyTextContent(
                    summary=f"Body summary for slide {i}.",
                    source_paragraphs=[i],
                    compression_applied=0.5,
                    original_text_start=None,
                ),
                quote=None,
                key_metaphor=None,
                scene_beat_id=None,
                labels=None,
            )
            for i in range(1, slide_count + 1)
        ],
    )
    defaults.update(overrides)
    return Task4Output(**defaults)


# =============================================================================
# Task 5: Visual Design Specification
# =============================================================================


def make_task5_output(**overrides) -> Task5Output:
    defaults = dict(
        design_system=DesignSystem(
            background=BackgroundSpec(color="#111111", texture="matte"),
            typography=Typography(
                headline=HeadlineTypography(
                    family="serif",
                    weight="bold",
                    style="title_case",
                ),
                body=BodyTypography(family="sans-serif", size="medium"),
                quote=QuoteTypography(family="serif", style="italic"),
            ),
            color_palette=ColorPalette(
                primary_accent="#ff4422",
                secondary_accent="#3355aa",
                allow_override=False,
                symbolism=[
                    ColorSymbol(color="#ff4422", meaning="urgency"),
                ],
            ),
            motif=Motif(
                type="unified",
                primary_visual="Rain on glass",
                fallback_elements=["drops", "reflections"],
                components=None,
                persistence=0.8,
            ),
            visual_style=VisualStyle(
                primary="photorealistic",
                secondary=None,
                forbidden=["cartoon"],
                transition_rule="Secondary style only at act boundaries",
            ),
            environmental_motif=None,
            layout_preferences=LayoutPreferences(
                diagram_heavy=False,
                comparison_percentage=0.2,
                preferred_patterns=["full-bleed"],
            ),
            special_techniques=[
                SpecialTechnique(
                    technique="match-cut",
                    when_to_use="between acts",
                ),
            ],
        ),
    )
    defaults.update(overrides)
    return Task5Output(**defaults)


# =============================================================================
# Task 6: Slide Specification
# =============================================================================


def make_task6_output(slide_count: int = 3, **overrides) -> Task6Output:
    slides = [
        SlideSpec(
            number=i,
            role="opening" if i == 1 else ("closing" if i == slide_count else "body"),
            content=SlideContent(
                headline=f"Slide {i} Headline",
                subheadline=None,
                body_text=f"Body {i}",
                quote=None,
                callout=None,
                labels=None,
            ),
            layout=SlideLayout(pattern="full-bleed", grid_description="12-col"),
            visual=SlideVisual(
                image_spec=ImageSpec(
                    subject=f"Subject {i}",
                    mood="contemplative",
                    color_temperature="cool",
                    metaphor_visualized=None,
                    scene_visualized=None,
                    characters_in_frame=None,
                    camera_angle=None,
                    key_action=None,
                    style_notes="photorealistic",
                ),
                color_usage=ColorUsage(
                    background="#111111",
                    accents_used=["#ff4422"],
                ),
                typography_notes="Bold headline",
            ),
            arc_position=ArcPosition(
                intensity=min(5, i + 1),
                function="opening" if i == 1 else "body",
                transition_to_next="cut",
            ),
        )
        for i in range(1, slide_count + 1)
    ]
    defaults = dict(slides=slides)
    defaults.update(overrides)
    return Task6Output(**defaults)


# =============================================================================
# Task 7: Image Prompt Generation
# =============================================================================


def make_image_prompt(slide_number: int = 1) -> ImagePrompt:
    return ImagePrompt(
        full_prompt=f"Full prompt text for slide {slide_number}.",
        sections=ImagePromptSections(
            goal="Create atmospheric image",
            subject="Rain on window",
            composition="Rule of thirds",
            setting="Dark office",
            lighting="Moody",
            text_elements=None,
            style="Photorealistic",
            fidelity="High",
            consistency="Maintain palette",
        ),
        generation_notes=GenerationNotes(
            aspect_ratio="16:9",
            negative_prompts=None,
            key_requirements=["dark tones", "rain"],
        ),
    )


def make_task7_output(slide_count: int = 3, **overrides) -> Task7Output:
    defaults = dict(
        slide_prompts=[
            SlideImagePrompt(
                slide_number=i,
                image_prompt=make_image_prompt(i),
            )
            for i in range(1, slide_count + 1)
        ],
    )
    defaults.update(overrides)
    return Task7Output(**defaults)
