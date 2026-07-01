"""End-to-end-ish tests for SlidePipeline.run_infographic_pipeline.

Uses MockTextClient + MockImageClient to drive the full pipeline without
touching any real provider. Covers: i0→i1→i2→images ordering, output-file
naming, manifest content, resume logic, skip_images, invalid arguments.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from polyptych.model_config import ModelConfig
from polyptych.models import (
    ContentStructure,
    GenerationNotes,
    InfographicColorPalette,
    InfographicKeyPoint,
    InfographicRelationship,
    InfographicSection,
    InfographicVariant,
    TaskI0Output,
    TaskI1Output,
    TaskI2Output,
    VisualizableData,
)
from polyptych.pipeline import (
    INFOGRAPHIC_OUTPUT_FILES,
    SlidePipeline,
)
from polyptych.run_config import InfographicRunConfig

from .mock_client import MockImageClient


@pytest.fixture
def infographic_model_config() -> ModelConfig:
    """Minimal config that resolves i0/i1/i2 to a stub model."""
    return ModelConfig(
        providers={"gemini": {"fast": "test-model", "thinking": "test-model"}},
        tasks={"i0": "thinking", "i1": "thinking", "i2": "thinking"},
        max_output_tokens={"i0": 16000, "i1": 16000, "i2": 16000},
        thinking_budget={},
    )


def _i0() -> TaskI0Output:
    return TaskI0Output(
        title="Test Infographic",
        subtitle="A short test subtitle.",
        thesis="The central thesis of the content.",
        key_points=[
            InfographicKeyPoint(
                id="KP1",
                statement="First key point.",
                importance="primary",
                source_paragraphs=[1],
            ),
            InfographicKeyPoint(
                id="KP2",
                statement="Second key point.",
                importance="secondary",
                source_paragraphs=[2],
            ),
        ],
        relationships=[
            InfographicRelationship(
                from_point="KP1",
                to_point="KP2",
                relationship_type="supports",
                label="leads to",
            ),
        ],
        visualizable_data=[
            VisualizableData(
                description="comparison data",
                data_type="comparison",
                values=["A", "B"],
            ),
        ],
        content_structure=ContentStructure(
            primary_pattern="argument",
            rationale="best fits the content",
            section_count=3,
        ),
        tone="analytical",
        target_audience="general readers",
    )


def _i1() -> TaskI1Output:
    return TaskI1Output(
        layout_type="vertical_flow",
        orientation="landscape",
        sections=[
            InfographicSection(
                title="Section A",
                content_summary="summary",
                visual_element="flowchart",
                visual_description="boxes connected with arrows",
                placement="full_width_top",
            ),
        ],
        color_palette=InfographicColorPalette(
            primary="#000000",
            secondary="#444444",
            accent="#ff0000",
            background="#ffffff",
            text="#222222",
            rationale="high contrast",
        ),
        typography_notes="sans serif, bold headers",
        visual_style="semi_flat",
        icon_style="line",
        title_treatment="bold serif at top",
        flow_description="top-to-bottom",
    )


def _variant(num: int = 1) -> InfographicVariant:
    return InfographicVariant(
        variant_number=num,
        interpretation=f"angle-{num}",
        full_prompt=(
            "GOAL: x\nSUBJECT: x\nCOMPOSITION: x\nSPATIAL_RELATIONSHIPS: x\n"
            "SETTING: x\nLIGHTING: x\nTEXT_ELEMENTS: x\nSTYLE: x\n"
            "FIDELITY: x\nCONSISTENCY: x"
        ),
        generation_notes=GenerationNotes(
            aspect_ratio="16:9",
            negative_prompts=None,
            key_requirements=["render TITLE verbatim"],
        ),
    )


def _build_pipeline(
    tmp_path: Path,
    source_text: str,
    mc: ModelConfig,
    mock_client,
) -> SlidePipeline:
    source_file = tmp_path / "source.md"
    source_file.write_text(source_text)
    output_dir = tmp_path / "output"
    pipeline = SlidePipeline(
        source_path=source_file,
        output_dir=output_dir,
        model_config=mc,
        text_provider="gemini",
        text_fallback=["none"],
    )
    pipeline.text_client = mock_client
    return pipeline


class TestRunInfographicPipeline:
    def test_runs_i0_i1_i2_then_images_in_order(
        self,
        tmp_path,
        source_text,
        infographic_model_config,
        mock_client,
    ):
        mock_client.register_structured("i0", _i0())
        mock_client.register_structured("i1", _i1())
        mock_client.register_structured("i2", TaskI2Output(variants=[_variant(1)]))
        pipeline = _build_pipeline(
            tmp_path,
            source_text,
            infographic_model_config,
            mock_client,
        )

        with patch.object(
            pipeline, "_make_image_client", return_value=MockImageClient()
        ):
            pipeline.run_infographic_pipeline(
                InfographicRunConfig(
                    provider="gemini",
                    num_variants=1,
                    skip_images=False,
                )
            )

        # Each task YAML must exist
        assert (pipeline.output_dir / INFOGRAPHIC_OUTPUT_FILES["i0"]).is_file()
        assert (pipeline.output_dir / INFOGRAPHIC_OUTPUT_FILES["i1"]).is_file()
        assert (pipeline.output_dir / INFOGRAPHIC_OUTPUT_FILES["i2"]).is_file()

        # Per-variant prompt yaml must exist
        assert (
            pipeline.output_dir / "prompts" / "infographic-v1-prompt.yaml"
        ).is_file()

        # Manifest captures pipeline + num_variants
        manifest = yaml.safe_load((pipeline.output_dir / "manifest.yaml").read_text())
        assert manifest["pipeline"] == "infographic"
        assert manifest["num_variants"] == 1

        # One image must be generated for one variant
        images = list((pipeline.output_dir / "images").glob("infographic-v1.*"))
        assert len(images) == 1

    def test_i2_negative_prompts_folded_into_full_prompt(
        self,
        tmp_path,
        source_text,
        infographic_model_config,
        mock_client,
    ):
        # TASK-102: providers send only full_prompt, so each variant's
        # negatives must be folded into the prompt text as an AVOID line.
        variant = _variant(1)
        variant.generation_notes.negative_prompts = [
            "blurry text",
            "photographic elements",
        ]
        mock_client.register_structured("i0", _i0())
        mock_client.register_structured("i1", _i1())
        mock_client.register_structured("i2", TaskI2Output(variants=[variant]))
        pipeline = _build_pipeline(
            tmp_path,
            source_text,
            infographic_model_config,
            mock_client,
        )

        with patch.object(
            pipeline, "_make_image_client", return_value=MockImageClient()
        ):
            pipeline.run_infographic_pipeline(
                InfographicRunConfig(
                    provider="gemini",
                    num_variants=1,
                    skip_images=True,
                )
            )

        avoid = "AVOID: blurry text, photographic elements."
        canonical = yaml.safe_load(
            (pipeline.output_dir / INFOGRAPHIC_OUTPUT_FILES["i2"]).read_text()
        )
        assert canonical["variants"][0]["full_prompt"].endswith(avoid)
        prompt_file = yaml.safe_load(
            (pipeline.output_dir / "prompts" / "infographic-v1-prompt.yaml").read_text()
        )
        assert avoid in prompt_file["full_prompt"]

    def test_skip_images_does_not_call_image_client(
        self,
        tmp_path,
        source_text,
        infographic_model_config,
        mock_client,
    ):
        mock_client.register_structured("i0", _i0())
        mock_client.register_structured("i1", _i1())
        mock_client.register_structured("i2", TaskI2Output(variants=[_variant(1)]))
        pipeline = _build_pipeline(
            tmp_path,
            source_text,
            infographic_model_config,
            mock_client,
        )

        called = {"count": 0}

        def _track(_provider):
            called["count"] += 1
            return MockImageClient()

        with patch.object(pipeline, "_make_image_client", side_effect=_track):
            pipeline.run_infographic_pipeline(
                InfographicRunConfig(
                    provider="gemini",
                    num_variants=1,
                    skip_images=True,
                )
            )

        assert called["count"] == 0
        assert (pipeline.output_dir / INFOGRAPHIC_OUTPUT_FILES["i2"]).is_file()
        images = list((pipeline.output_dir / "images").glob("infographic-*"))
        assert images == []

    def test_invalid_from_step_raises(
        self,
        tmp_path,
        source_text,
        infographic_model_config,
        mock_client,
    ):
        pipeline = _build_pipeline(
            tmp_path,
            source_text,
            infographic_model_config,
            mock_client,
        )
        with pytest.raises(ValueError, match="Invalid from_step"):
            pipeline.run_infographic_pipeline(InfographicRunConfig(from_step="bogus"))

    def test_invalid_to_step_raises(
        self,
        tmp_path,
        source_text,
        infographic_model_config,
        mock_client,
    ):
        pipeline = _build_pipeline(
            tmp_path,
            source_text,
            infographic_model_config,
            mock_client,
        )
        with pytest.raises(ValueError, match="Invalid to_step"):
            pipeline.run_infographic_pipeline(InfographicRunConfig(to_step="bogus"))

    def test_from_after_to_raises(
        self,
        tmp_path,
        source_text,
        infographic_model_config,
        mock_client,
    ):
        pipeline = _build_pipeline(
            tmp_path,
            source_text,
            infographic_model_config,
            mock_client,
        )
        with pytest.raises(ValueError, match="is after"):
            pipeline.run_infographic_pipeline(
                InfographicRunConfig(from_step="i2", to_step="i0")
            )

    def test_resume_from_i1_loads_i0_dependency(
        self,
        tmp_path,
        source_text,
        infographic_model_config,
        mock_client,
    ):
        # Pre-write a valid i0 yaml so resuming from i1 succeeds.
        pipeline = _build_pipeline(
            tmp_path,
            source_text,
            infographic_model_config,
            mock_client,
        )
        pipeline._save_yaml(_i0().model_dump(), INFOGRAPHIC_OUTPUT_FILES["i0"])

        mock_client.register_structured("i1", _i1())
        mock_client.register_structured("i2", TaskI2Output(variants=[_variant(1)]))

        with patch.object(
            pipeline, "_make_image_client", return_value=MockImageClient()
        ):
            pipeline.run_infographic_pipeline(
                InfographicRunConfig(
                    provider="gemini",
                    num_variants=1,
                    from_step="i1",
                    skip_images=True,
                )
            )

        # i0 must NOT have been called (was loaded from disk)
        assert mock_client.call_count("structured:i0") == 0
        # i1 was called exactly once
        assert mock_client.call_count("structured:i1") == 1

    def test_existing_image_is_skipped(
        self,
        tmp_path,
        source_text,
        infographic_model_config,
        mock_client,
    ):
        mock_client.register_structured("i0", _i0())
        mock_client.register_structured("i1", _i1())
        mock_client.register_structured("i2", TaskI2Output(variants=[_variant(1)]))
        pipeline = _build_pipeline(
            tmp_path,
            source_text,
            infographic_model_config,
            mock_client,
        )

        # Pre-write a fake image so the pipeline skips regeneration
        (pipeline.output_dir / "images").mkdir(parents=True, exist_ok=True)
        existing = pipeline.output_dir / "images" / "infographic-v1.png"
        existing.write_bytes(b"fake-png")

        image_client = MockImageClient()
        with patch.object(pipeline, "_make_image_client", return_value=image_client):
            pipeline.run_infographic_pipeline(
                InfographicRunConfig(
                    provider="gemini",
                    num_variants=1,
                    skip_images=False,
                )
            )

        assert existing.read_bytes() == b"fake-png"
        assert image_client._call_count == 0

    def test_to_i1_stops_before_i2(
        self,
        tmp_path,
        source_text,
        infographic_model_config,
        mock_client,
    ):
        """to_step='i1' should not run i2 or images."""
        mock_client.register_structured("i0", _i0())
        mock_client.register_structured("i1", _i1())
        pipeline = _build_pipeline(
            tmp_path,
            source_text,
            infographic_model_config,
            mock_client,
        )

        with patch.object(
            pipeline, "_make_image_client", return_value=MockImageClient()
        ):
            pipeline.run_infographic_pipeline(
                InfographicRunConfig(
                    provider="gemini",
                    num_variants=1,
                    to_step="i1",
                )
            )

        assert (pipeline.output_dir / INFOGRAPHIC_OUTPUT_FILES["i0"]).is_file()
        assert (pipeline.output_dir / INFOGRAPHIC_OUTPUT_FILES["i1"]).is_file()
        # i2 must NOT have been called or written
        assert mock_client.call_count("structured:i2") == 0
        assert not (pipeline.output_dir / INFOGRAPHIC_OUTPUT_FILES["i2"]).exists()


class TestInfographicValidatorRegistration:
    def test_infographic_steps_registered(self):
        from polyptych import cli  # noqa: F401
        from polyptych.pipeline import (
            INFOGRAPHIC_MODELS,
            INFOGRAPHIC_OUTPUT_FILES,
            INFOGRAPHIC_STEPS,
        )

        assert INFOGRAPHIC_STEPS == ["i0", "i1", "i2", "images"]
        assert "i0" in INFOGRAPHIC_OUTPUT_FILES
        assert INFOGRAPHIC_MODELS["i0"].__name__ == "TaskI0Output"
        assert INFOGRAPHIC_MODELS["i1"].__name__ == "TaskI1Output"
        assert INFOGRAPHIC_MODELS["i2"].__name__ == "TaskI2Output"
