"""Tests for polyptych.clean_source."""

from polyptych.clean_source import (
    CleaningConfig,
    clean_source,
    clean_file,
    remove_toc,
    remove_image_refs,
    remove_footnote_blocks,
    remove_footnote_superscripts,
    remove_page_numbers,
    unescape_chars,
    normalize_whitespace,
)


class TestRemoveToc:
    def test_removes_toc_with_dot_leaders(self):
        text = (
            "Some preamble\n"
            "\n"
            "**CONTENTS**\n"
            "\n"
            "**1. INTRODUCTION................................................................................................... 1**\n"
            "\n"
            "*Who is John Boyd?...................................................................................1*\n"
            "\n"
            "**2. ON STRATEGY................................................... 13**\n"
            "\n"
            "**1. INTRODUCTION**\n"
            "\n"
            "The actual content starts here."
        )
        result, count = remove_toc(text)
        assert "CONTENTS" not in result
        assert "....." not in result
        assert "**1. INTRODUCTION**" in result
        assert "The actual content starts here." in result
        assert count > 0

    def test_preserves_text_before_toc(self):
        text = (
            "Title line\n\n**CONTENTS**\n\n**1. Foo.....1**\n\n**1. Foo**\n\nContent."
        )
        result, _ = remove_toc(text)
        assert "Title line" in result

    def test_no_toc_returns_unchanged(self):
        text = "No table of contents here.\n\nJust content."
        result, count = remove_toc(text)
        assert result == text
        assert count == 0


class TestRemoveImageRefs:
    def test_removes_image_ref_and_caption(self):
        text = (
            "Some text before.\n"
            "\n"
            "*![][image1]*\n"
            "First Lt. John Boyd in the cockpit\n"
            "\n"
            "Some text after."
        )
        result, count = remove_image_refs(text)
        assert "![][image1]" not in result
        assert "cockpit" not in result
        assert "Some text before." in result
        assert "Some text after." in result
        assert count == 1

    def test_removes_image_ref_without_asterisks(self):
        text = "Before.\n\n![][image2]\nCaption line\n\nAfter."
        result, count = remove_image_refs(text)
        assert "image2" not in result
        assert count == 1

    def test_no_image_refs(self):
        text = "Just normal text.\n\nNo images here."
        result, count = remove_image_refs(text)
        assert result == text
        assert count == 0


class TestRemoveFootnoteBlocks:
    def test_removes_footnote_block(self):
        text = (
            "the power of his intellect.\n"
            "\n"
            "    \n"
            "1 General C.C. Krulak, Commandant of the Marine Corps, Inside the Pentagon, 13 March 1997, p.5.\n"
            "2 Colin Gray, Modern Strategy (Oxford, 1999), p. 52.\n"
            "\n"
            "The next paragraph continues."
        )
        result, count = remove_footnote_blocks(text)
        assert "Krulak" not in result
        assert "Colin Gray" not in result
        assert "The next paragraph continues." in result
        assert count > 0

    def test_removes_multi_footnote_blocks(self):
        text = (
            "Content before.\n"
            "\n"
            "    \n"
            "3 Hammond, p.56.\n"
            "\n"
            "4 Robert Coram, Boyd (2002), p.451.\n"
            "\n"
            "Content after."
        )
        result, count = remove_footnote_blocks(text)
        assert "Hammond" not in result
        assert "Coram" not in result
        assert "Content before." in result
        assert "Content after." in result

    def test_preserves_numbered_list(self):
        text = "Things to do:\n\n1. First item\n2. Second item\n3. Third item\n\nEnd."
        result, count = remove_footnote_blocks(text)
        # Numbered lists use ". " not just " " after the number
        assert "First item" in result
        assert "Second item" in result

    def test_no_footnotes(self):
        text = "Just regular text.\n\nMore text."
        result, count = remove_footnote_blocks(text)
        assert result == text


class TestRemoveFootnoteSuperscripts:
    def test_strips_superscript_after_word(self):
        text = "the power of his intellect1."
        result, count = remove_footnote_superscripts(text)
        assert result == "the power of his intellect."
        assert count == 1

    def test_strips_multiple_superscripts(self):
        text = "war2. Boyd was important3, and influential4."
        result, count = remove_footnote_superscripts(text)
        assert result == "war. Boyd was important, and influential."
        assert count == 3

    def test_strips_large_superscript(self):
        text = "forces120."
        result, count = remove_footnote_superscripts(text)
        assert result == "forces."
        assert count == 1

    def test_preserves_dates(self):
        text = "In 1997, Boyd died."
        result, count = remove_footnote_superscripts(text)
        assert "1997" in result

    def test_preserves_model_numbers(self):
        text = "the F-16 and F-86 aircraft"
        result, count = remove_footnote_superscripts(text)
        assert "F-16" in result
        assert "F-86" in result

    def test_preserves_standalone_numbers(self):
        text = "There were 120 soldiers."
        result, count = remove_footnote_superscripts(text)
        assert "120" in result

    def test_superscript_before_comma(self):
        text = "Boyd7, a strategist"
        result, count = remove_footnote_superscripts(text)
        assert result == "Boyd, a strategist"
        assert count == 1

    def test_superscript_at_end_of_line(self):
        text = "the OODA loop5"
        result, count = remove_footnote_superscripts(text)
        assert result == "the OODA loop"
        assert count == 1


class TestRemovePageNumbers:
    def test_removes_arabic_page_numbers(self):
        text = "End of page.\n\n1   \n\nStart of next page."
        result, count = remove_page_numbers(text)
        assert "1   " not in result
        assert "End of page." in result
        assert "Start of next page." in result
        assert count == 1

    def test_removes_multiple_page_numbers(self):
        text = "Text.\n\n12\n\nMore text.\n\n13\n\nEnd."
        result, count = remove_page_numbers(text)
        assert "12" not in result.split("\n")
        assert "13" not in result.split("\n")
        assert count == 2

    def test_removes_roman_numerals_in_front_matter(self):
        text = "Front matter.\n\nvii\n\nMore front.\n\n**1. CHAPTER**\n\nContent."
        result, count = remove_page_numbers(text)
        assert count == 1
        assert "vii" not in [line.strip() for line in result.split("\n")]

    def test_preserves_roman_after_chapter(self):
        text = "**1. CHAPTER**\n\nContent.\n\nvii\n\nMore."
        result, count = remove_page_numbers(text)
        # Roman numeral after first chapter should be preserved
        assert count == 0

    def test_preserves_numbers_in_text(self):
        text = "There were 12 chapters in the book."
        result, count = remove_page_numbers(text)
        assert "12" in result
        assert count == 0

    def test_preserves_numbers_not_surrounded_by_blanks(self):
        text = "Line before\n42\nLine after"
        result, count = remove_page_numbers(text)
        assert "42" in result
        assert count == 0


class TestUnescapeChars:
    def test_unescape_period(self):
        result, count = unescape_chars(r"1\. INTRODUCTION")
        assert result == "1. INTRODUCTION"
        assert count == 1

    def test_unescape_plus(self):
        result, count = unescape_chars(r"\+31 (0)15")
        assert result == "+31 (0)15"

    def test_unescape_hyphen(self):
        result, count = unescape_chars(r"POST\-MODERN")
        assert result == "POST-MODERN"

    def test_unescape_brackets(self):
        result, count = unescape_chars(r"\[text\]")
        assert result == "[text]"

    def test_unescape_parens(self):
        result, count = unescape_chars(r"\(text\)")
        assert result == "(text)"

    def test_multiple_escapes(self):
        text = r"1\. Chapter \- Section \+ Notes"
        result, count = unescape_chars(text)
        assert result == "1. Chapter - Section + Notes"
        assert count == 3

    def test_no_escapes(self):
        result, count = unescape_chars("Plain text with no escapes.")
        assert result == "Plain text with no escapes."
        assert count == 0


class TestNormalizeWhitespace:
    def test_collapses_excess_blank_lines(self):
        text = "Para 1.\n\n\n\n\nPara 2."
        result = normalize_whitespace(text)
        assert result == "Para 1.\n\n\nPara 2."

    def test_strips_trailing_whitespace(self):
        text = "Line with trailing spaces   \nAnother line  "
        result = normalize_whitespace(text)
        assert result == "Line with trailing spaces\nAnother line"

    def test_preserves_double_blank(self):
        text = "Para 1.\n\nPara 2."
        result = normalize_whitespace(text)
        assert result == text


class TestCleanSource:
    def test_all_passes_run(self):
        text = (
            "Title\n"
            "\n"
            "*![][image1]*\n"
            "Caption\n"
            "\n"
            "Content with intellect1.\n"
            "\n"
            r"1\. Escaped heading"
            "\n"
            "\n"
            "42\n"
            "\n"
            "More content."
        )
        result, stats = clean_source(text)
        assert "![][image1]" not in result
        assert "intellect." in result
        assert "1. Escaped heading" in result
        assert stats.image_refs_removed == 1
        assert stats.escapes_fixed > 0

    def test_config_disables_passes(self):
        text = r"1\. Escaped" "\n\n*![][image1]*\nCaption"
        config = CleaningConfig(
            remove_toc=False,
            remove_image_refs=False,
            remove_footnotes=False,
            remove_page_numbers=False,
            unescape_chars=False,
        )
        result, stats = clean_source(text, config)
        assert r"1\." in result
        assert "image1" in result

    def test_idempotency(self):
        text = (
            "Title\n\n"
            "*![][image1]*\n"
            "Caption\n\n"
            "Some text with ref1.\n\n"
            r"1\. Chapter"
            "\n\n"
            "    \n"
            "1 Footnote text.\n\n"
            "42\n\n"
            "Content."
        )
        first_pass, _ = clean_source(text)
        second_pass, stats2 = clean_source(first_pass)
        assert first_pass == second_pass

    def test_integration_thesis_snippet(self):
        """Integration test with a representative snippet from OsingaBoydThesis.md."""
        text = (
            "**CONTENTS**\n"
            "\n"
            "**1\\. INTRODUCTION................................................................................................... 1**\n"
            "\n"
            "*Who is John Boyd?...................................................................................1*\n"
            "\n"
            "**1\\. INTRODUCTION**\n"
            "\n"
            "*![][image1]*\n"
            "First Lt. John Boyd in the cockpit of an F-86\n"
            "\n"
            "a towering intellect who made unsurpassed contributions1.\n"
            "Boyd was a strategist2. He flew the F-86 Sabre during the Korean War.\n"
            "He retired as a colonel in 1975\\.\n"
            "\n"
            "    \n"
            "1 General C.C. Krulak, Commandant of the Marine Corps, p.5.\n"
            "2 Colin Gray, Modern Strategy (Oxford, 1999), p. 52\\.\n"
            "\n"
            "1   \n"
            "\n"
            "The next paragraph continues.\n"
            "Phone: \\+31 (0)15-2131484\n"
        )
        result, stats = clean_source(text)

        # TOC removed
        assert "CONTENTS" not in result
        assert "....." not in result

        # Image ref removed
        assert "![][image1]" not in result
        assert "cockpit" not in result

        # Footnote superscripts stripped
        assert "contributions." in result
        assert "strategist." in result
        assert "contributions1" not in result

        # F-86 preserved (model number)
        assert "F-86" in result

        # 1975 preserved (year)
        assert "1975" in result

        # Footnote block removed
        assert "Krulak" not in result

        # Page number removed
        assert "\n1   \n" not in result

        # Escapes fixed
        assert "\\+" not in result
        assert "+31" in result
        assert "1975." in result


class TestCleanFile:
    def test_writes_output(self, tmp_path):
        input_file = tmp_path / "test.md"
        input_file.write_text("Content with ref1.\n\n42\n\nMore.")

        out_path, result = clean_file(input_file)
        assert out_path == tmp_path / "test-clean.md"
        assert out_path.exists()
        cleaned = out_path.read_text()
        assert "Content with ref." in cleaned

    def test_custom_output_path(self, tmp_path):
        input_file = tmp_path / "source.md"
        input_file.write_text("Hello world.")
        output_file = tmp_path / "output.md"

        out_path, _ = clean_file(input_file, output_file)
        assert out_path == output_file
        assert output_file.exists()

    def test_with_config(self, tmp_path):
        input_file = tmp_path / "test.md"
        input_file.write_text(r"1\. Escaped")
        config = CleaningConfig(unescape_chars=False)

        out_path, result = clean_file(input_file, config=config)
        content = out_path.read_text()
        assert r"1\." in content
