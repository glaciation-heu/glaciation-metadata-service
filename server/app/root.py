from fastapi import APIRouter
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER

router = APIRouter()


@router.get(
    "/",
    operation_id="root__get",
    summary="Redirect to Swagger",
    status_code=HTTP_303_SEE_OTHER,
    include_in_schema=False,
)
async def read() -> RedirectResponse:
    """Redirect to Swagger"""
    return RedirectResponse(url="/docs", status_code=HTTP_303_SEE_OTHER)
