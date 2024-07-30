from typing import Any, Dict

from io import StringIO
from json import dumps

from fastapi import APIRouter
from rdflib import Graph
from SPARQLWrapper.SmartWrapper import Bindings
from starlette.responses import RedirectResponse
from starlette.status import HTTP_303_SEE_OTHER

from app.consts import EMPTY_SEARCH_RESPONSE, TagEnum
from app.FusekiCommunicator import FusekiCommunicatior
from app.schemas import (
    ResponseHead,
    ResponseResults,
    SearchResponse,
    SPARQLQuery,
    UpdateRequestBody,
)

router = APIRouter(tags=[TagEnum.GRAPH])

fuseki_jena_url = "jena-fuseki.integration"
fuseki_jena_port = None
fuseki_jena_dataset_name = "cheese"
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
    body: UpdateRequestBody,
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
) -> SearchResponse:
    """Execute SPARQL search query and return a response in JSON format."""
    result = fuseki.read_query(query)

    if type(result) is Bindings:
        bindings = []
        for item in result.bindings:
            new_item: Dict[str, Any] = {}
            for key in item:
                new_item[key] = {}
                for property in item[key].__dict__:
                    if (
                        property != "variable"
                        and item[key].__dict__[property] is not None
                    ):
                        new_item[key][property] = item[key].__dict__[property]
                        if property == "lang":
                            new_item[key]["xml:lang"] = new_item[key].pop("lang")
            bindings.append(new_item)

        return SearchResponse(
            head=ResponseHead(vars=result.head["vars"]),
            results=ResponseResults(bindings=bindings),
        )

    return EMPTY_SEARCH_RESPONSE
