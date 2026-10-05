import pytest

from docs_qa.library.enums import FileFormat
from docs_qa.library.errors import UnsupportedFileError
from docs_qa.library.file_format import detect_file_format


@pytest.mark.parametrize(
    ("file_name", "content", "expected"),
    [
        ("policy.PDF", b"%PDF-1.7 ...", FileFormat.PDF),
        ("guide.md", b"# Guide", FileFormat.MARKDOWN),
        ("notes.markdown", b"text", FileFormat.MARKDOWN),
        ("notes.txt", b"text", FileFormat.PLAIN_TEXT),
    ],
)
def test_detects_supported_formats(file_name: str, content: bytes, expected: FileFormat) -> None:
    assert detect_file_format(file_name, content) is expected


@pytest.mark.parametrize(
    ("file_name", "content"),
    [
        ("report.docx", b"PK..."),
        ("fake.pdf", b"not a pdf"),
        ("binary.txt", b"\xff\xfe\x00"),
        ("no-extension", b"text"),
    ],
)
def test_rejects_unsupported_files(file_name: str, content: bytes) -> None:
    with pytest.raises(UnsupportedFileError):
        detect_file_format(file_name, content)
