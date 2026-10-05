import httpx
import pytest
from fastapi import status

from tests.integration.conftest import READER_KEY, drain
from tests.integration.sample_documents import EXPENSE_POLICY, LEAVE_POLICY

pytestmark = pytest.mark.integration


async def create_collection(client: httpx.AsyncClient, name: str = "Handbook") -> str:
    response = await client.post("/api/collections", json={"name": name})
    assert response.status_code == status.HTTP_201_CREATED
    collection_id: str = response.json()["id"]
    return collection_id


async def upload(
    client: httpx.AsyncClient, collection_id: str, name: str, content: bytes
) -> httpx.Response:
    return await client.post(
        f"/api/collections/{collection_id}/documents", files={"file": (name, content)}
    )


async def test_uploaded_document_becomes_ready_with_chunks(client, worker) -> None:
    collection_id = await create_collection(client)

    uploaded = await upload(client, collection_id, "leave.md", LEAVE_POLICY)
    await drain(worker)

    assert uploaded.status_code == status.HTTP_201_CREATED
    assert uploaded.json()["status"] == "UPLOADED"
    document = (await client.get(f"/api/documents/{uploaded.json()['id']}")).json()
    assert document["status"] == "READY"
    assert document["chunkCount"] >= 2
    collections = (await client.get("/api/collections")).json()
    assert collections[0]["readyDocumentCount"] == 1


async def test_uploading_the_same_file_twice_returns_the_existing_document(client) -> None:
    collection_id = await create_collection(client)

    first = await upload(client, collection_id, "leave.md", LEAVE_POLICY)
    second = await upload(client, collection_id, "copy-of-leave.md", LEAVE_POLICY)

    assert second.status_code == status.HTTP_200_OK
    assert second.json()["id"] == first.json()["id"]


async def test_unsupported_file_is_rejected_as_problem_details(client) -> None:
    collection_id = await create_collection(client)

    response = await upload(client, collection_id, "report.docx", b"PK\x03\x04")

    assert response.status_code == status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["title"] == "Unsupported file"


async def test_file_without_text_fails_and_can_be_retried(client, worker) -> None:
    collection_id = await create_collection(client)
    uploaded = await upload(client, collection_id, "blank.md", b"# Title only\n")

    await drain(worker)
    failed = (await client.get(f"/api/documents/{uploaded.json()['id']}")).json()
    retried = await client.post(f"/api/documents/{uploaded.json()['id']}/retry")

    assert failed["status"] == "FAILED"
    assert "no text" in failed["failureReason"]
    assert retried.json()["status"] == "UPLOADED"


async def test_new_version_replaces_the_old_one_once_ready(client, worker) -> None:
    collection_id = await create_collection(client)
    original = await upload(client, collection_id, "leave.md", LEAVE_POLICY)
    await drain(worker)

    version = await client.post(
        f"/api/documents/{original.json()['id']}/versions",
        files={"file": ("leave.md", LEAVE_POLICY + b"\nParental leave is sixteen weeks.\n")},
    )
    listed_before = (await client.get(f"/api/collections/{collection_id}/documents")).json()
    await drain(worker)
    listed_after = (await client.get(f"/api/collections/{collection_id}/documents")).json()

    assert version.json()["replacesDocumentId"] == original.json()["id"]
    assert {d["status"] for d in listed_before} == {"READY", "UPLOADED"}
    assert [d["id"] for d in listed_after] == [version.json()["id"]]


async def test_deleting_a_document_removes_it_from_search(client, worker) -> None:
    collection_id = await create_collection(client)
    leave = await upload(client, collection_id, "leave.md", LEAVE_POLICY)
    await upload(client, collection_id, "expenses.md", EXPENSE_POLICY)
    await drain(worker)

    await client.delete(f"/api/documents/{leave.json()['id']}")
    search = await client.post(
        f"/api/collections/{collection_id}/search", json={"query": "sick leave days"}
    )

    assert {hit["fileName"] for hit in search.json()["hits"]} == {"expenses.md"}


async def test_duplicate_collection_name_is_a_conflict(client) -> None:
    await create_collection(client, "Handbook")

    response = await client.post("/api/collections", json={"name": "Handbook"})

    assert response.status_code == status.HTTP_409_CONFLICT


async def test_reader_cannot_upload(client) -> None:
    collection_id = await create_collection(client)

    response = await client.post(
        f"/api/collections/{collection_id}/documents",
        files={"file": ("leave.md", LEAVE_POLICY)},
        headers={"X-Api-Key": READER_KEY},
    )

    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_request_without_api_key_is_unauthorized(client) -> None:
    response = await client.get("/api/collections", headers={"X-Api-Key": ""})

    assert response.status_code == status.HTTP_401_UNAUTHORIZED
