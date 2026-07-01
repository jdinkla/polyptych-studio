"""Tests for the I2 critique-refine loop in the infographic pipeline.

Mirrors the anime critique tests: MockTextClient dispatches pre-registered
responses by task name; assertions check call counts, saved artifacts, and
the canonical output after refinement.
"""

from __future__ import annotations

import yaml

from polyptych.model_config import ModelConfig
from polyptych.models import (
    I2PromptIssue,
    TaskI2Critique,
    TaskI2Output,
)
from polyptych.pipeline import INFOGRAPHIC_OUTPUT_FILES
from polyptych.run_config import InfographicRunConfig
from polyptych.tasks.task_i2_critique import _needs_refinement

from .test_pipeline_infographic import _build_pipeline, _i0, _i1, _variant


def _model_config() -> ModelConfig:
    return ModelConfig(
        providers={"gemini": {"fast": "test-model", "thinking": "test-model"}},
        tasks={
            "i0": "thinking",
            "i1": "thinking",
            "i2": "thinking",
            "i2_critique": "thinking",
            "i2_refine": "fast",
        },
        max_output_tokens={
            "i0": 16000,
            "i1": 16000,
            "i2": 16000,
            "i2_critique": 8000,
            "i2_refine": 16000,
        },
        thinking_budget={},
    )


def _critique(has_issues: bool) -> TaskI2Critique:
    issues = []
    if has_issues:
        issues.append(
            I2PromptIssue(
                variant_number=1,
                issue_type="color_inconsistency",
                description="AGI box is orange in the strip but purple in the flow.",
                severity="critical",
                suggested_fix="Use orange for AGI everywhere.",
            )
        )
    return TaskI2Critique(
        prompt_issues=issues,
        dropped_key_content=[],
        overall_assessment="ok" if not has_issues else "fix colors",
    )


def _minor_critique() -> TaskI2Critique:
    return TaskI2Critique(
        prompt_issues=[
            I2PromptIssue(
                variant_number=1,
                issue_type="vague_or_overloaded",
                description="Section header could be more specific.",
                severity="minor",
                suggested_fix="Name the section explicitly.",
            )
        ],
        dropped_key_content=[],
        overall_assessment="polish only",
    )


class TestNeedsRefinement:
    def test_empty_critique_needs_no_refinement(self):
        assert not _needs_refinement(_critique(has_issues=False))

    def test_minor_issues_need_no_refinement(self):
        assert not _needs_refinement(_minor_critique())

    def test_critical_issue_needs_refinement(self):
        assert _needs_refinement(_critique(has_issues=True))

    def test_important_issue_needs_refinement(self):
        critique = _critique(has_issues=True)
        critique.prompt_issues[0].severity = "important"
        assert _needs_refinement(critique)


class TestI2CritiqueLoop:
    def _run(self, tmp_path, source_text, mock_client, **config_kwargs):
        pipeline = _build_pipeline(tmp_path, source_text, _model_config(), mock_client)
        pipeline.run_infographic_pipeline(
            InfographicRunConfig(
                provider="gemini",
                num_variants=1,
                skip_images=True,
                to_step="i2",
                **config_kwargs,
            )
        )
        return pipeline

    def test_default_skips_critique(self, tmp_path, source_text, mock_client):
        mock_client.register_structured("i0", _i0())
        mock_client.register_structured("i1", _i1())
        mock_client.register_structured("i2", TaskI2Output(variants=[_variant(1)]))

        pipeline = self._run(tmp_path, source_text, mock_client)

        assert mock_client.call_count("structured:i2") == 1
        assert mock_client.call_count("structured:i2_critique") == 0
        assert mock_client.call_count("structured:i2_refine") == 0
        assert (pipeline.output_dir / INFOGRAPHIC_OUTPUT_FILES["i2"]).is_file()
        # Manifest records the loop as disabled
        manifest = yaml.safe_load((pipeline.output_dir / "manifest.yaml").read_text())
        assert manifest["critique_rounds"] == 0

    def test_clean_critique_skips_refine(self, tmp_path, source_text, mock_client):
        mock_client.register_structured("i0", _i0())
        mock_client.register_structured("i1", _i1())
        mock_client.register_structured("i2", TaskI2Output(variants=[_variant(1)]))
        mock_client.register_structured("i2_critique", _critique(has_issues=False))

        pipeline = self._run(
            tmp_path,
            source_text,
            mock_client,
            skip_critique=False,
            critique_rounds=2,
        )

        assert mock_client.call_count("structured:i2_critique") == 1
        assert mock_client.call_count("structured:i2_refine") == 0
        # v1 + critique artifacts saved; canonical equals v1
        assert (pipeline.output_dir / "task-i2-1-prompts.yaml").is_file()
        assert (pipeline.output_dir / "task-i2-2-critique.yaml").is_file()
        assert not (pipeline.output_dir / "task-i2-3-prompts.yaml").exists()

    def test_issues_trigger_refine_and_canonical_is_refined(
        self, tmp_path, source_text, mock_client
    ):
        refined = TaskI2Output(variants=[_variant(1)])
        refined.variants[0].interpretation = "refined-angle"

        mock_client.register_structured("i0", _i0())
        mock_client.register_structured("i1", _i1())
        mock_client.register_structured("i2", TaskI2Output(variants=[_variant(1)]))
        mock_client.register_structured("i2_critique", _critique(has_issues=True))
        mock_client.register_structured("i2_refine", refined)

        pipeline = self._run(
            tmp_path,
            source_text,
            mock_client,
            skip_critique=False,
            critique_rounds=1,
        )

        assert mock_client.call_count("structured:i2_critique") == 1
        assert mock_client.call_count("structured:i2_refine") == 1
        # Intermediate artifacts
        assert (pipeline.output_dir / "task-i2-1-prompts.yaml").is_file()
        assert (pipeline.output_dir / "task-i2-2-critique.yaml").is_file()
        assert (pipeline.output_dir / "task-i2-3-prompts.yaml").is_file()
        # Canonical output and per-variant prompt files reflect the refined version
        canonical = yaml.safe_load(
            (pipeline.output_dir / INFOGRAPHIC_OUTPUT_FILES["i2"]).read_text()
        )
        assert canonical["variants"][0]["interpretation"] == "refined-angle"
        prompt_file = yaml.safe_load(
            (pipeline.output_dir / "prompts" / "infographic-v1-prompt.yaml").read_text()
        )
        assert prompt_file["interpretation"] == "refined-angle"
        # Manifest records the enabled loop
        manifest = yaml.safe_load((pipeline.output_dir / "manifest.yaml").read_text())
        assert manifest["critique_rounds"] == 1

    def test_refined_variant_negatives_are_folded(
        self, tmp_path, source_text, mock_client
    ):
        # TASK-102: the refine pass replaces variants wholesale, so its output
        # needs the same deterministic AVOID-line fold as the initial i2 call.
        refined_variant = _variant(1)
        refined_variant.generation_notes.negative_prompts = ["clip art", "gradients"]
        refined = TaskI2Output(variants=[refined_variant])

        mock_client.register_structured("i0", _i0())
        mock_client.register_structured("i1", _i1())
        mock_client.register_structured("i2", TaskI2Output(variants=[_variant(1)]))
        mock_client.register_structured("i2_critique", _critique(has_issues=True))
        mock_client.register_structured("i2_refine", refined)

        pipeline = self._run(
            tmp_path,
            source_text,
            mock_client,
            skip_critique=False,
            critique_rounds=1,
        )

        canonical = yaml.safe_load(
            (pipeline.output_dir / INFOGRAPHIC_OUTPUT_FILES["i2"]).read_text()
        )
        assert canonical["variants"][0]["full_prompt"].endswith(
            "AVOID: clip art, gradients."
        )
