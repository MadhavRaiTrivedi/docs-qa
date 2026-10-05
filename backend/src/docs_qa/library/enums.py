from enum import StrEnum


class FileFormat(StrEnum):
    PDF = "PDF"
    MARKDOWN = "MARKDOWN"
    PLAIN_TEXT = "PLAIN_TEXT"


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"
