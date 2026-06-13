---
name: clean-source
description: Clean PDF-converted markdown files by removing page numbers, footnotes, TOC, broken images, and escaped characters
argument-hint: <input-file> [--output <file>] [--keep-footnotes] [--keep-toc]
---

# Clean Source — PDF Markdown Cleanup

## Role

You clean PDF-to-markdown conversion artifacts from source files before they are fed into pipelines.

## Arguments

Parse from `$ARGUMENTS`:
- **input-file** (required): Path to the markdown file to clean
- Optional flags: `--output`, `--keep-toc`, `--keep-images`, `--keep-footnotes`, `--keep-page-numbers`, `--keep-escapes`, `--dry-run`

If the input file is missing, ask the user.

## Process

1. **Verify file exists** — check the input file path
2. **Run cleaning** — execute `uv run polyptych clean-source <file> [flags]`
3. **Report results** — show the cleaning statistics (lines removed, artifacts found)
4. **Suggest next step** — recommend running a pipeline with the cleaned file, e.g.:
   - `/run-local-pipeline slide <cleaned-file>`
   - `/run-pipeline slide <cleaned-file> <output-dir>`

## Tips

- Use `--dry-run` first to preview what will be removed without writing
- Use `--keep-footnotes` if the source uses inline citations that should be preserved
- The default output is `<stem>-clean.md` in the same directory as the input
