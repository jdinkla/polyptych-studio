"""Tests for polyptych.text_utils."""

from polyptych.text_utils import (
    fold_negatives_into_prompt,
    number_paragraphs,
    parse_paragraphs,
)


class TestFoldNegativesIntoPrompt:
    def test_appends_avoid_line(self):
        result = fold_negatives_into_prompt("GOAL: x", ["blurry text", "modern"])
        assert result == "GOAL: x\n\nAVOID: blurry text, modern."

    def test_none_leaves_prompt_unchanged(self):
        assert fold_negatives_into_prompt("GOAL: x", None) == "GOAL: x"

    def test_empty_list_leaves_prompt_unchanged(self):
        assert fold_negatives_into_prompt("GOAL: x", []) == "GOAL: x"

    def test_blank_entries_are_dropped(self):
        result = fold_negatives_into_prompt("GOAL: x", ["  ", "", "color"])
        assert result == "GOAL: x\n\nAVOID: color."

    def test_all_blank_entries_leave_prompt_unchanged(self):
        assert fold_negatives_into_prompt("GOAL: x", ["  ", ""]) == "GOAL: x"

    def test_idempotent(self):
        once = fold_negatives_into_prompt("GOAL: x", ["color", "modern"])
        twice = fold_negatives_into_prompt(once, ["color", "modern"])
        assert twice == once


class TestParseParagraphs:
    def test_single_paragraph(self):
        assert parse_paragraphs("Hello world.") == {1: "Hello world."}

    def test_multiple_paragraphs(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        result = parse_paragraphs(text)
        assert result == {
            1: "First paragraph.",
            2: "Second paragraph.",
            3: "Third paragraph.",
        }

    def test_leading_trailing_whitespace(self):
        text = "\n\n  Hello world.  \n\n"
        assert parse_paragraphs(text) == {1: "Hello world."}

    def test_empty_string(self):
        assert parse_paragraphs("") == {}

    def test_blank_lines_with_spaces(self):
        text = "Para one.\n  \n  \nPara two."
        result = parse_paragraphs(text)
        assert len(result) == 2
        assert result[1] == "Para one."
        assert result[2] == "Para two."

    def test_multiline_paragraph(self):
        text = "Line one\nline two\nline three\n\nSecond paragraph."
        result = parse_paragraphs(text)
        assert len(result) == 2
        assert "line two" in result[1]
        assert result[2] == "Second paragraph."

    def test_one_indexed(self):
        result = parse_paragraphs("A\n\nB")
        assert 1 in result
        assert 0 not in result


class TestNumberParagraphs:
    def test_single_paragraph(self):
        assert number_paragraphs("Hello world.") == "[1] Hello world."

    def test_multiple_paragraphs(self):
        text = "First.\n\nSecond.\n\nThird."
        result = number_paragraphs(text)
        assert result == "[1] First.\n\n[2] Second.\n\n[3] Third."

    def test_empty_string(self):
        assert number_paragraphs("") == ""

    def test_leading_trailing_whitespace(self):
        result = number_paragraphs("\n\n  Hello.  \n\n")
        assert result == "[1] Hello."

    def test_blank_lines_with_spaces(self):
        result = number_paragraphs("A.\n  \n  \nB.")
        assert "[1] A." in result
        assert "[2] B." in result

    def test_multiline_paragraph_preserved(self):
        text = "Line one\nline two\n\nSecond."
        result = number_paragraphs(text)
        assert result.startswith("[1] Line one\nline two")
        assert "[2] Second." in result

    def test_consistent_with_parse_paragraphs(self):
        """number_paragraphs and parse_paragraphs use the same splitting logic."""
        text = "Alpha.\n\nBeta.\n\nGamma.\n\nDelta."
        parsed = parse_paragraphs(text)
        numbered = number_paragraphs(text)
        # Each [N] in numbered output should correspond to key N in parsed
        for key, value in parsed.items():
            assert f"[{key}] {value}" in numbered
