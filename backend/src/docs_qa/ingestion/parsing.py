import re
from dataclasses import dataclass
from io import BytesIO
from typing import Protocol

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from docs_qa.library.enums import FileFormat
from docs_qa.library.models import ChunkLocation


class DocumentParseError(Exception):
    pass


@dataclass(frozen=True)
class Section:
    text: str
    location: ChunkLocation


@dataclass(frozen=True)
class ParsedDocument:
    sections: list[Section]
    page_count: int | None = None


class DocumentParser(Protocol):
    def parse(self, content: bytes) -> ParsedDocument: ...


class PdfParser:
    def parse(self, content: bytes) -> ParsedDocument:
        try:
            reader = PdfReader(BytesIO(content))
            pages = [page.extract_text() for page in reader.pages]
        except PdfReadError as error:
            raise DocumentParseError(f"The PDF could not be read: {error}") from error

        sections = [
            Section(text, ChunkLocation(page_number=number))
            for number, text in enumerate(pages, start=1)
            if text.strip()
        ]
        return ParsedDocument(sections, page_count=len(pages))


_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_FENCE = re.compile(r"^\s*(```|~~~)")


class MarkdownParser:
    """Splits a Markdown file at its headings so every section knows the headings above it."""

    def parse(self, content: bytes) -> ParsedDocument:
        sections: list[Section] = []
        headings: list[tuple[int, str]] = []
        lines: list[str] = []
        is_in_code_block = False

        def close_section() -> None:
            text = "\n".join(lines).strip()
            if text:
                path = tuple(title for _, title in headings)
                sections.append(Section(text, ChunkLocation(heading_path=path)))
            lines.clear()

        for line in _decode(content).splitlines():
            if _FENCE.match(line):
                is_in_code_block = not is_in_code_block
            heading = None if is_in_code_block else _HEADING.match(line)
            if heading is None:
                lines.append(line)
                continue

            close_section()
            level = len(heading.group(1))
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, heading.group(2)))

        close_section()
        return ParsedDocument(sections)


class PlainTextParser:
    def parse(self, content: bytes) -> ParsedDocument:
        text = _decode(content).strip()
        return ParsedDocument([Section(text, ChunkLocation())] if text else [])


_PARSERS: dict[FileFormat, DocumentParser] = {
    FileFormat.PDF: PdfParser(),
    FileFormat.MARKDOWN: MarkdownParser(),
    FileFormat.PLAIN_TEXT: PlainTextParser(),
}


def parser_for(file_format: FileFormat) -> DocumentParser:
    return _PARSERS[file_format]


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DocumentParseError("The file is not UTF-8 text.") from error
