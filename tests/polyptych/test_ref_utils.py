"""Tests for polyptych.ref_utils."""

from __future__ import annotations

import pytest

from polyptych.ref_utils import find_style_exemplar


# =============================================================================
# find_style_exemplar
# =============================================================================


class TestFindStyleExemplar:
    def test_returns_none_when_path_is_none(self):
        assert find_style_exemplar(None) is None

    def test_returns_none_when_md_does_not_exist(self, tmp_path):
        missing = tmp_path / "noir.md"
        assert find_style_exemplar(missing) is None

    def test_returns_none_when_no_companion_image(self, tmp_path):
        style_md = tmp_path / "noir.md"
        style_md.write_text("# Noir style")
        assert find_style_exemplar(style_md) is None

    def test_finds_png_companion(self, tmp_path):
        style_md = tmp_path / "noir.md"
        style_md.write_text("# Noir")
        png = tmp_path / "noir.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n")
        assert find_style_exemplar(style_md) == png

    @pytest.mark.parametrize("ext", [".jpg", ".jpeg", ".webp"])
    def test_finds_other_companion_extensions(self, tmp_path, ext):
        style_md = tmp_path / "noir.md"
        style_md.write_text("# Noir")
        companion = tmp_path / f"noir{ext}"
        companion.write_bytes(b"fake-image-data")
        assert find_style_exemplar(style_md) == companion

    def test_png_wins_over_jpg_when_both_present(self, tmp_path):
        # Iteration order is .png, .jpg, .jpeg, .webp — first match wins.
        style_md = tmp_path / "noir.md"
        style_md.write_text("# Noir")
        (tmp_path / "noir.jpg").write_bytes(b"j")
        png = tmp_path / "noir.png"
        png.write_bytes(b"p")
        assert find_style_exemplar(style_md) == png

    def test_accepts_string_path(self, tmp_path):
        style_md = tmp_path / "noir.md"
        style_md.write_text("# Noir")
        png = tmp_path / "noir.png"
        png.write_bytes(b"p")
        assert find_style_exemplar(str(style_md)) == png

    def test_does_not_match_directory_with_image_suffix(self, tmp_path):
        # ``with_suffix`` could conceivably match a directory; verify is_file
        # gating rejects that.
        style_md = tmp_path / "noir.md"
        style_md.write_text("# Noir")
        (tmp_path / "noir.png").mkdir()
        assert find_style_exemplar(style_md) is None
