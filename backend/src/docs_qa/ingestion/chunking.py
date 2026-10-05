import re
from collections.abc import Iterator
from dataclasses import dataclass

from docs_qa.ingestion.parsing import Section
from docs_qa.library.models import ChunkLocation

_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")


@dataclass(frozen=True)
class ChunkDraft:
    text: str
    location: ChunkLocation
    word_count: int


class Chunker:
    """Packs whole paragraphs into chunks of at most `max_words` words.

    A chunk never crosses a section boundary, so its page or heading stays exact. Consecutive
    chunks of a section share `overlap_words` words, so a sentence cut at a boundary is still
    found whole in one of them.
    """

    def __init__(self, max_words: int, overlap_words: int) -> None:
        if not 0 <= overlap_words < max_words:
            raise ValueError("overlap_words must be at least 0 and smaller than max_words.")
        self._max_words = max_words
        self._overlap_words = overlap_words

    def split(self, sections: list[Section]) -> list[ChunkDraft]:
        return [draft for section in sections for draft in self._split_section(section)]

    def _split_section(self, section: Section) -> Iterator[ChunkDraft]:
        parts: list[str] = []
        word_count = 0
        has_new_words = False

        for paragraph in self._paragraphs(section.text):
            paragraph_words = len(paragraph.split())
            if has_new_words and word_count + paragraph_words > self._max_words:
                yield ChunkDraft("\n\n".join(parts), section.location, word_count)
                overlap = self._tail_words(parts)
                parts = [overlap] if overlap else []
                word_count = len(overlap.split())
                has_new_words = False

            parts.append(paragraph)
            word_count += paragraph_words
            has_new_words = True

        if has_new_words:
            yield ChunkDraft("\n\n".join(parts), section.location, word_count)

    def _paragraphs(self, text: str) -> Iterator[str]:
        # A paragraph plus the overlap carried in from the previous chunk must still fit.
        step = self._max_words - self._overlap_words
        for paragraph in _PARAGRAPH_BREAK.split(text):
            words = paragraph.split()
            if len(words) <= step:
                if words:
                    yield paragraph.strip()
                continue
            for start in range(0, len(words), step):
                yield " ".join(words[start : start + step])

    def _tail_words(self, parts: list[str]) -> str:
        if self._overlap_words == 0:
            return ""
        return " ".join(" ".join(parts).split()[-self._overlap_words :])
