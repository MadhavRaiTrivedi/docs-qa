from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from docs_qa.auth.api_key import RequireReader
from docs_qa.dependencies import get_retriever
from docs_qa.search.hybrid_retriever import HybridRetriever
from docs_qa.search.schemas import SearchRequest, SearchResponse

router = APIRouter(tags=["search"], dependencies=[RequireReader])


@router.post("/collections/{collection_id}/search")
async def search(
    collection_id: UUID,
    request: SearchRequest,
    retriever: Annotated[HybridRetriever, Depends(get_retriever)],
) -> SearchResponse:
    return SearchResponse.from_result(await retriever.retrieve(collection_id, request.query))
