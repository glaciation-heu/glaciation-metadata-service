from fastapi import APIRouter
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER

from app.consts import TagEnum

router = APIRouter(tags=[TagEnum.GRAPH])


@router.get(
    "/",
    status_code=HTTP_303_SEE_OTHER,
    include_in_schema=False,
)
async def read_root() -> RedirectResponse:
    """Redirect to Swagger"""
    return RedirectResponse(url="/docs", status_code=HTTP_303_SEE_OTHER)


@router.patch(
    "/api/v0/graph",
)
async def update_graph() -> str:
    """Update Distributed Knowledge Graph"""
    return "Success"
