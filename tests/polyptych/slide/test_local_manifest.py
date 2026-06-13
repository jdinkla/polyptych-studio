"""Local-skill manifest interop (TASK-85).

Local runs (/run-local-pipeline, /run-local-task, /infographic) write a
manifest.yaml with `mode: local`, `models: claude-local`, and
`tasks_completed`. A later CLI resume must not be confused by those fields:
the CLI rewrites the manifest wholesale and consumers read it as a plain
dict, so extra keys are harmless.
"""

from __future__ import annotations

import yaml

from polyptych.pipeline import SlidePipeline
from polyptych.run_config import SlideRunConfig


LOCAL_MANIFEST = {
    "pipeline": "slide",
    "mode": "local",
    "timestamp": "2026-06-13T00:00:00+00:00",
    "git_commit": "abc1234",
    "source": "source.md",
    "models": "claude-local",
    "style_prompt": "prompts/style-transfer/noir/film-noir.md",
    "tasks_completed": ["task1", "task2", "task3"],
}


class TestCliOverwritesLocalManifest:
    def test_write_manifest_replaces_local_one_without_error(
        self, slide_pipeline: SlidePipeline
    ) -> None:
        manifest_path = slide_pipeline.output_dir / "manifest.yaml"
        manifest_path.write_text(yaml.safe_dump(LOCAL_MANIFEST))

        config = SlideRunConfig(from_step="images", to_step="images")
        slide_pipeline._write_manifest("slide", config)

        updated = yaml.safe_load(manifest_path.read_text())
        # Rewritten as a CLI manifest: same overlapping field names …
        assert updated["pipeline"] == "slide"
        assert updated["source"] == "source.md"
        assert "git_commit" in updated
        # … and the local-only markers are gone (full CLI provenance now).
        assert "mode" not in updated
        assert "tasks_completed" not in updated
        assert updated["models"] != "claude-local"
