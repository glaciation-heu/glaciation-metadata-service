from typing import Annotated, Any

from fastapi import APIRouter, Body
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER

from app.consts import TagEnum
from app.FusekiCommunicator import FusekiCommunicatior

router = APIRouter(tags=[TagEnum.GRAPH])

fuseki_jena_url = "localhost"
fuseki_jena_port = 3030
fuseki_jena_dataset_name = "slice"
fuseki = FusekiCommunicatior(
    fuseki_jena_url, fuseki_jena_port, fuseki_jena_dataset_name
)


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
async def update_graph(
    body: Annotated[
        dict[str, Any],
        Body(
            description=(
                "Request body must be in JSON-LD format. "
                "It must be compatible with GLACIATION metadata upper ontology."
            ),
        ),
    ]
) -> str:
    """Update Distributed Knowledge Graph"""
    if "sparql" in body:
        fuseki.update_query(body["sparql"])
        return "Success"
    return "Failure"
