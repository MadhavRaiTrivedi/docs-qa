import pytest

from docs_qa.ingestion.parsing import (
    DocumentParseError,
    MarkdownParser,
    PdfParser,
    PlainTextParser,
)

MARKDOWN = b"""Intro line.

# Leave policy

General rules.

## Sick leave

Twelve days a year.

```python
# not a heading
```

## Annual leave ##

Twenty days.

# Expenses

Keep receipts.
"""


def test_markdown_sections_carry_their_heading_path() -> None:
    parsed = MarkdownParser().parse(MARKDOWN)

    paths = [section.location.heading_path for section in parsed.sections]
    assert paths == [
        (),
        ("Leave policy",),
        ("Leave policy", "Sick leave"),
        ("Leave policy", "Annual leave"),
        ("Expenses",),
    ]


def test_markdown_ignores_hash_lines_inside_code_blocks() -> None:
    parsed = MarkdownParser().parse(MARKDOWN)

    sick_leave = parsed.sections[2]
    assert "# not a heading" in sick_leave.text


def test_markdown_skips_headings_without_text() -> None:
    parsed = MarkdownParser().parse(b"# Empty\n\n# Filled\n\nBody.")

    assert [section.location.heading_path for section in parsed.sections] == [("Filled",)]


def test_plain_text_becomes_one_section() -> None:
    parsed = PlainTextParser().parse("﻿Line one.\n\nLine two.".encode())

    assert len(parsed.sections) == 1
    assert parsed.sections[0].text == "Line one.\n\nLine two."


def test_text_that_is_not_utf8_fails() -> None:
    with pytest.raises(DocumentParseError):
        PlainTextParser().parse(b"\xff\xfe\x00broken")


def test_unreadable_pdf_fails() -> None:
    with pytest.raises(DocumentParseError):
        PdfParser().parse(b"%PDF-1.7 truncated")
