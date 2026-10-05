---
id: TASK-6
title: Add a transcript mode to clean-source
status: To Do
assignee: []
created_date: '2026-10-05 16:19'
labels:
  - delegate
  - source-cleaning
dependencies: []
priority: medium
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
polyptych clean-source (src/polyptych/clean_source.py) only removes PDF-conversion artifacts. Podcast/video transcripts arrive as alternating timestamp lines (e.g. '1:27:58') and text lines with no blank lines, so number_paragraphs() in src/polyptych/text_utils.py sees one paragraph and every i0 source_paragraphs reference becomes [1], which makes /trace-prompt useless. Add a --transcript mode that produces paragraph-structured text.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 'polyptych clean-source FILE --transcript' removes lines matching ^\d+:\d{2}(:\d{2})?$ and joins the remaining lines into running text
- [ ] #2 It splits the text into paragraphs of roughly 120-200 words, breaking only at sentence ends (. ? !), separated by blank lines, so number_paragraphs() yields more than one paragraph
- [ ] #3 Optional --glossary PATH loads a YAML mapping of wrong to right terms (e.g. Kremmel: Kreml) applied as whole-word replacements
- [ ] #4 Bracketed sound annotations such as [musik], [gelächter], [räuspern] are removed
- [ ] #5 Unit tests use a small fixture transcript and assert paragraph count, timestamp removal, and glossary replacement; 'just test' and 'just lint' pass
- [ ] #6 docs/reference/cli-reference.md and the clean-source skill document the flag
<!-- AC:END -->
