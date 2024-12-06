from typing import Any, Dict

from io import StringIO
from json import dumps
from os import getenv
from re import findall
from time import time

from fastapi import APIRouter, HTTPException
from loguru import logger
from rdflib import ConjunctiveGraph
from requests import post
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

fuseki_jena_url = getenv("TRIPLE_STORE_URL", "jena-fuseki")
fuseki_jena_port = getenv("TRIPLE_STORE_PORT")
fuseki_jena_dataset_name = getenv("TRIPLE_STORE_DATASET", "slice")
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
    g = ConjunctiveGraph()
    g.parse(StringIO(dumps(body)), format="json-ld")

    ts = int(time() * 1000)  # current timestamp
    n_triples = 0

    graph_name = ""
    if "@id" in body:
        graph_name = body["@id"]
        if graph_name[-1] != "/":
            graph_name += "/"

    query = "INSERT DATA {\n"
    query += "\tGRAPH <%stimestamp:%d> {\n" % (graph_name, ts)
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
        logger.debug(
            f"Inserted {n_triples} triple(s) into graph <{graph_name}timestamp:{ts}>."
        )
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


@router.get(
    "/api/v0/graph/update",
)
async def perform_update_query(
    query: SPARQLQuery,
) -> str:
    """Execute SPARQL update query and return a response."""
    queries = findall(r"DROP GRAPH <.*?>;?", query)
    if len(queries) == 0:
        queries = [query]

    for single_query in queries:
        valid, msg = fuseki.validate_sparql(single_query, "update")

        if valid:
            fuseki.update_query(single_query)
        else:
            logger.error(msg)
            logger.debug(f"The query:\n{single_query}")
            raise HTTPException(HTTP_400_BAD_REQUEST, msg)

    return "Success"


@router.post(
    "/api/v0/graph/compact",
)
async def perform_compaction() -> str:
    port_placeholder = f":{fuseki_jena_port}" if fuseki_jena_port is not None else ""
    url = f"http://{fuseki_jena_url}{port_placeholder}/$/compact/{fuseki_jena_dataset_name}"

    params = {"deleteOld": "true"}

    try:
        response = post(url, params=params)

        if response.status_code == 200:
            logger.info("Compaction triggered successfully!")
            logger.debug(response.text)
            return "Success"
        else:
            logger.error(f"Compaction failed: {response.text}")
            raise HTTPException(HTTP_500_INTERNAL_SERVER_ERROR, response.text)
    except Exception as e:
        logger.exception("An unexpected error occurred during compaction.")
        raise HTTPException(HTTP_500_INTERNAL_SERVER_ERROR, str(e))
