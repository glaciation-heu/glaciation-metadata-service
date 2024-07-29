from typing import Annotated, Any

from io import StringIO
from json import dumps

from fastapi import APIRouter, Body
from rdflib import Graph
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER

from app.consts import TagEnum
from app.FusekiCommunicator import FusekiCommunicatior
from app.schemas import SearchResponse, SPARQLQuery

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
    g = Graph()
    g.parse(StringIO(dumps(body)), format="json-ld")

    query = "INSERT DATA {\n"
    for s, p, o in g.triples((None, None, None)):
        if hasattr(s, "n3") and hasattr(p, "n3") and hasattr(o, "n3"):
            query += "\t" + s.n3() + " " + p.n3() + " " + o.n3() + " .\n"
        else:
            return "Failure"
    query += "}"

    fuseki.update_query(query)

    return "Success"


@router.get(
    "/api/v0/graph",
)
async def search_graph(
    query: SPARQLQuery,
) -> SearchResponse | None:
    # result = fuseki.read_query(query)
    # if type(result) is Bindings:
    #     bindings = []
    #     for item in result.bindings:
    #         new_item = {}
    #         for key in item:
    #             if hasattr(item[key], "value") and hasattr(item[key], "type"):
    #                 new_item[key] = {"value": item[key].value, "type": item[key].type}
    #         bindings.append(new_item)
    #     return bindings
    # else:
    #     return str(result)
    return None  # Delete me!
