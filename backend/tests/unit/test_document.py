import uuid
from datetime import UTC, datetime, timedelta

import pytest

from docs_qa.library.enums import DocumentStatus, FileFormat
from docs_qa.library.errors import InvalidDocumentTransitionError, LeaseLostError
from docs_qa.library.models import Document

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
LEASE_SECONDS = 300


def uploaded_document() -> Document:
    return Document.upload(uuid.uuid4(), "leave.md", FileFormat.MARKDOWN, b"# Leave")


def test_upload_starts_in_uploaded_with_content_hash() -> None:
    document = uploaded_document()

    assert document.status is DocumentStatus.UPLOADED
    assert document.attempts == 0
    assert len(document.content_sha256) == 64


def test_start_processing_takes_a_lease_and_counts_the_attempt() -> None:
    document = uploaded_document()

    token = document.start_processing(NOW, LEASE_SECONDS)

    assert document.status is DocumentStatus.PROCESSING
    assert document.lease_token == token
    assert document.lease_expires_at == NOW + timedelta(seconds=LEASE_SECONDS)
    assert document.attempts == 1


def test_mark_ready_with_the_current_lease_releases_it() -> None:
    document = uploaded_document()
    token = document.start_processing(NOW, LEASE_SECONDS)

    document.mark_ready(token, page_count=None, now=NOW)

    assert document.status is DocumentStatus.READY
    assert document.lease_token is None
    assert document.ready_at == NOW


def test_mark_ready_after_the_lease_was_taken_over_raises() -> None:
    document = uploaded_document()
    stale_token = document.start_processing(NOW, LEASE_SECONDS)
    document.start_processing(NOW + timedelta(seconds=LEASE_SECONDS + 1), LEASE_SECONDS)

    with pytest.raises(LeaseLostError):
        document.mark_ready(stale_token, page_count=None, now=NOW)


def test_reclaiming_an_expired_lease_counts_another_attempt() -> None:
    document = uploaded_document()
    document.start_processing(NOW, LEASE_SECONDS)

    document.start_processing(NOW + timedelta(seconds=LEASE_SECONDS + 1), LEASE_SECONDS)

    assert document.attempts == 2
    assert document.has_exhausted_attempts(max_attempts=2)


def test_retry_moves_a_failed_document_back_to_uploaded() -> None:
    document = uploaded_document()
    document.start_processing(NOW, LEASE_SECONDS)
    document.mark_failed("No text")

    document.retry()

    assert document.status is DocumentStatus.UPLOADED
    assert document.attempts == 0
    assert document.failure_reason is None


@pytest.mark.parametrize("status", [DocumentStatus.UPLOADED, DocumentStatus.READY])
def test_retry_when_not_failed_raises(status: DocumentStatus) -> None:
    document = uploaded_document()
    document.status = status

    with pytest.raises(InvalidDocumentTransitionError):
        document.retry()


def test_ready_document_cannot_be_processed_again() -> None:
    document = uploaded_document()
    token = document.start_processing(NOW, LEASE_SECONDS)
    document.mark_ready(token, page_count=None, now=NOW)

    with pytest.raises(InvalidDocumentTransitionError):
        document.start_processing(NOW, LEASE_SECONDS)
