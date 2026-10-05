from uuid import UUID

from docs_qa.library.enums import DocumentStatus


class InvalidDocumentTransitionError(Exception):
    def __init__(self, document_id: UUID, current: DocumentStatus, target: DocumentStatus) -> None:
        super().__init__(f"Document {document_id} cannot move from {current} to {target}.")
        self.document_id = document_id
        self.current = current
        self.target = target


class LeaseLostError(Exception):
    """The worker's claim on a document expired and another worker took it over."""

    def __init__(self, document_id: UUID) -> None:
        super().__init__(f"The lease on document {document_id} is no longer held.")


class DuplicateCollectionNameError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"A collection named '{name}' already exists.")


class UnsupportedFileError(Exception):
    pass


BYTES_PER_MEGABYTE = 1024 * 1024


class FileTooLargeError(Exception):
    def __init__(self, max_file_size_bytes: int) -> None:
        super().__init__(
            f"Files larger than {max_file_size_bytes // BYTES_PER_MEGABYTE} MB are rejected."
        )
