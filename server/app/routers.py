from typing import Any, Dict

from io import StringIO
from json import dumps
from time import time

from fastapi import APIRouter, HTTPException
from loguru import logger
from rdflib import Graph
from SPARQLWrapper.SmartWrapper import Bindings
from starlette.responses import RedirectResponse
from starlette.status import (
    HTTP_303_SEE_OTHER,
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

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

fuseki_jena_url = "jena-fuseki"
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
    body: UpdateRequestBody,
) -> str:
    """Update Distributed Knowledge Graph"""
    g = Graph()
    g.parse(StringIO(dumps(body)), format="json-ld")

    ts = int(time() * 1000)  # current timestamp
    n_triples = 0

    query = "INSERT DATA {\n"
    query += "\tGRAPH <timestamp:%d> {\n" % ts
    for s, p, o in g.triples((None, None, None)):
        if hasattr(s, "n3") and hasattr(p, "n3") and hasattr(o, "n3"):
            query += f"\t\t{s.n3()} {p.n3()} {o.n3()} .\n"
            n_triples += 1
        else:
            raise HTTPException(
                HTTP_500_INTERNAL_SERVER_ERROR, "Error in parsing JSON-LD."
            )
    query += "\t}\n"
    query += "}"

    valid, msg = fuseki.validate_sparql(query, "update")

    if n_triples == 0:
        logger.error("No triples could be extracted from JSON-LD.")
        raise HTTPException(
            HTTP_400_BAD_REQUEST, "No triples could be extracted from JSON-LD."
        )
    elif valid:
        fuseki.update_query(query)
        logger.debug(f"Inserted {n_triples} triple(s) into graph <timastamp:{ts}>.")
    else:
        logger.error(msg)
        logger.debug(f"The query:\n{query}")
        raise HTTPException(HTTP_500_INTERNAL_SERVER_ERROR, msg)

    return "Success"


@router.get(
    "/api/v0/graph",
)
async def search_graph(
    query: SPARQLQuery,
) -> SearchResponse:
    """Execute SPARQL search query and return a response in JSON format."""
    valid, msg = fuseki.validate_sparql(query, "query")

    if valid:
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
    else:
        logger.error(msg)
        logger.debug(f"The query:\n{query}")
        raise HTTPException(HTTP_400_BAD_REQUEST, msg)

    return EMPTY_SEARCH_RESPONSE
