from pathlib import PurePath

from docs_qa.library.enums import FileFormat
from docs_qa.library.errors import UnsupportedFileError

_FORMATS_BY_EXTENSION = {
    ".pdf": FileFormat.PDF,
    ".md": FileFormat.MARKDOWN,
    ".markdown": FileFormat.MARKDOWN,
    ".txt": FileFormat.PLAIN_TEXT,
}
_PDF_SIGNATURE = b"%PDF-"


def detect_file_format(file_name: str, content: bytes) -> FileFormat:
    extension = PurePath(file_name).suffix.lower()
    file_format = _FORMATS_BY_EXTENSION.get(extension)
    if file_format is None:
        supported = ", ".join(sorted(_FORMATS_BY_EXTENSION))
        raise UnsupportedFileError(
            f"'{extension or file_name}' files are not supported. Use {supported}."
        )

    if file_format is FileFormat.PDF and not content.startswith(_PDF_SIGNATURE):
        raise UnsupportedFileError(f"{file_name} does not look like a PDF file.")

    if file_format is not FileFormat.PDF:
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise UnsupportedFileError(f"{file_name} is not UTF-8 text.") from error

    return file_format
