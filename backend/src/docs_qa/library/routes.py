from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, UploadFile, status

from docs_qa.auth.api_key import RequireEditor, RequireReader
from docs_qa.dependencies import AppSettings, get_collection_service, get_document_service
from docs_qa.library.collection_service import CollectionOverview, CollectionService
from docs_qa.library.document_service import DocumentService, UploadOutcome
from docs_qa.library.errors import FileTooLargeError, UnsupportedFileError
from docs_qa.library.schemas import CollectionRequest, CollectionResponse, DocumentResponse

router = APIRouter(tags=["library"])

Collections = Annotated[CollectionService, Depends(get_collection_service)]
Documents = Annotated[DocumentService, Depends(get_document_service)]


@router.get("/collections", dependencies=[RequireReader])
async def list_collections(collections: Collections) -> list[CollectionResponse]:
    return [CollectionResponse.from_overview(overview) for overview in await collections.list()]


@router.post("/collections", status_code=status.HTTP_201_CREATED, dependencies=[RequireEditor])
async def create_collection(
    request: CollectionRequest, collections: Collections
) -> CollectionResponse:
    collection = await collections.create(request.name)
    return CollectionResponse.from_overview(CollectionOverview(collection, 0, 0))


@router.get("/collections/{collection_id}", dependencies=[RequireReader])
async def get_collection(collection_id: UUID, collections: Collections) -> CollectionResponse:
    return CollectionResponse.from_overview(await collections.get_overview(collection_id))


@router.patch("/collections/{collection_id}", dependencies=[RequireEditor])
async def rename_collection(
    collection_id: UUID, request: CollectionRequest, collections: Collections
) -> CollectionResponse:
    await collections.rename(collection_id, request.name)
    return CollectionResponse.from_overview(await collections.get_overview(collection_id))


@router.delete(
    "/collections/{collection_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[RequireEditor],
)
async def delete_collection(collection_id: UUID, collections: Collections) -> None:
    await collections.delete(collection_id)


@router.get("/collections/{collection_id}/documents", dependencies=[RequireReader])
async def list_documents(collection_id: UUID, documents: Documents) -> list[DocumentResponse]:
    return [
        DocumentResponse.from_overview(overview) for overview in await documents.list(collection_id)
    ]


@router.post(
    "/collections/{collection_id}/documents",
    status_code=status.HTTP_201_CREATED,
    dependencies=[RequireEditor],
    responses={status.HTTP_200_OK: {"description": "The same file is already in the collection."}},
)
async def upload_document(
    collection_id: UUID,
    file: UploadFile,
    response: Response,
    documents: Documents,
    settings: AppSettings,
) -> DocumentResponse:
    file_name, content = await _read_upload(file, settings.upload.max_file_size_bytes)
    outcome = await documents.upload(collection_id, file_name, content)
    return await _upload_response(outcome, response, documents)


@router.get("/documents/{document_id}", dependencies=[RequireReader])
async def get_document(document_id: UUID, documents: Documents) -> DocumentResponse:
    return DocumentResponse.from_overview(await documents.get_overview(document_id))


@router.post(
    "/documents/{document_id}/versions",
    status_code=status.HTTP_201_CREATED,
    dependencies=[RequireEditor],
)
async def upload_document_version(
    document_id: UUID,
    file: UploadFile,
    response: Response,
    documents: Documents,
    settings: AppSettings,
) -> DocumentResponse:
    file_name, content = await _read_upload(file, settings.upload.max_file_size_bytes)
    outcome = await documents.upload_version(document_id, file_name, content)
    return await _upload_response(outcome, response, documents)


@router.post("/documents/{document_id}/retry", dependencies=[RequireEditor])
async def retry_document(document_id: UUID, documents: Documents) -> DocumentResponse:
    return DocumentResponse.from_document(await documents.retry(document_id))


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[RequireEditor],
)
async def delete_document(document_id: UUID, documents: Documents) -> None:
    await documents.delete(document_id)


async def _read_upload(file: UploadFile, max_file_size_bytes: int) -> tuple[str, bytes]:
    if not file.filename:
        raise UnsupportedFileError("The upload has no file name.")
    content = await file.read(max_file_size_bytes + 1)
    if len(content) > max_file_size_bytes:
        raise FileTooLargeError(max_file_size_bytes)
    if not content:
        raise UnsupportedFileError(f"{file.filename} is empty.")
    return file.filename, content


async def _upload_response(
    outcome: UploadOutcome, response: Response, documents: DocumentService
) -> DocumentResponse:
    if not outcome.is_duplicate:
        return DocumentResponse.from_document(outcome.document)
    response.status_code = status.HTTP_200_OK
    return DocumentResponse.from_overview(await documents.get_overview(outcome.document.id))
