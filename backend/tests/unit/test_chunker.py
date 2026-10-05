import pytest

from docs_qa.ingestion.chunking import Chunker
from docs_qa.ingestion.parsing import Section
from docs_qa.library.models import ChunkLocation

LOCATION = ChunkLocation(heading_path=("Leave",))


def words(count: int, prefix: str = "w") -> str:
    return " ".join(f"{prefix}{index}" for index in range(count))


def test_split_keeps_short_paragraphs_together() -> None:
    chunker = Chunker(max_words=50, overlap_words=5)

    drafts = chunker.split([Section("First paragraph.\n\nSecond paragraph.", LOCATION)])

    assert len(drafts) == 1
    assert drafts[0].text == "First paragraph.\n\nSecond paragraph."
    assert drafts[0].location == LOCATION


def test_split_never_exceeds_max_words() -> None:
    chunker = Chunker(max_words=20, overlap_words=5)
    text = "\n\n".join(words(8, prefix=f"p{n}-") for n in range(10))

    drafts = chunker.split([Section(text, LOCATION)])

    assert len(drafts) > 1
    assert all(draft.word_count <= 20 for draft in drafts)
    assert all(draft.word_count == len(draft.text.split()) for draft in drafts)


def test_consecutive_chunks_share_the_overlap() -> None:
    chunker = Chunker(max_words=20, overlap_words=5)
    text = "\n\n".join(words(8, prefix=f"p{n}-") for n in range(4))

    first, second, *_ = chunker.split([Section(text, LOCATION)])

    assert second.text.split()[:5] == first.text.split()[-5:]


def test_long_paragraph_is_cut_into_windows() -> None:
    chunker = Chunker(max_words=20, overlap_words=5)

    drafts = chunker.split([Section(words(100), LOCATION)])

    assert all(draft.word_count <= 20 for draft in drafts)
    covered = {word for draft in drafts for word in draft.text.split()}
    assert covered == set(words(100).split())


def test_chunks_do_not_cross_sections() -> None:
    chunker = Chunker(max_words=50, overlap_words=5)
    other = ChunkLocation(heading_path=("Expenses",))

    drafts = chunker.split([Section("Leave text.", LOCATION), Section("Expense text.", other)])

    assert [draft.location for draft in drafts] == [LOCATION, other]


def test_overlap_alone_is_never_emitted_as_a_chunk() -> None:
    chunker = Chunker(max_words=10, overlap_words=3)

    drafts = chunker.split([Section(f"{words(7)}\n\n{words(7, prefix='x')}", LOCATION)])

    assert len(drafts) == 2


def test_overlap_must_be_smaller_than_the_chunk() -> None:
    with pytest.raises(ValueError, match="overlap_words"):
        Chunker(max_words=10, overlap_words=10)
