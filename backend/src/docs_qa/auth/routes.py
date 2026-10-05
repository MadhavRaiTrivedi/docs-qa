from typing import Annotated

from fastapi import APIRouter, Depends

from docs_qa.api_model import ApiModel
from docs_qa.auth.api_key import current_role
from docs_qa.auth.role import Role

router = APIRouter(tags=["auth"])


class MeResponse(ApiModel):
    role: Role


@router.get("/me")
async def me(role: Annotated[Role, Depends(current_role)]) -> MeResponse:
    return MeResponse(role=role)
