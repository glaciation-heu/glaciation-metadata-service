from typing import Any, Dict

from io import StringIO
from json import dumps
from time import time

from fastapi import APIRouter, HTTPException
from loguru import logger
from rdflib import ConjunctiveGraph, Graph, URIRef, Literal, BNode
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

fuseki_jena_url = "jena-fuseki-test"
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


timestamps_query = """PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?graphURI WHERE {
  GRAPH ?graphURI {}
  FILTER regex(str(?graphURI), "^timestamp:")
}
ORDER BY ASC(xsd:integer(replace(str(?graphURI), "^timestamp:", "")))
"""


def perform_query(query: SPARQLQuery, fuseki: FusekiCommunicatior) -> SearchResponse:
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
    print(msg)
    return EMPTY_SEARCH_RESPONSE


def compose_insert_query_form_graph(g: ConjunctiveGraph, graph_name: str) -> str:
    n_triples = 0
    query = "INSERT DATA {\n"
    query += "\tGRAPH " + graph_name + " {\n"  # "\tGRAPH <timestamp:%d> {\n" % ts
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

    # return query, valid, msg
    if n_triples == 0:
        logger.error("No triples could be extracted from Graph")
        raise HTTPException(
            HTTP_400_BAD_REQUEST, "No triples could be extracted from Graph."
        )

    elif valid:
        logger.debug(f"Return query with {n_triples} triple(s) and name {graph_name}.")
        return query, n_triples, graph_name
    else:
        logger.error(msg)
        logger.debug(f"The query:\n{query}")
        raise HTTPException(HTTP_500_INTERNAL_SERVER_ERROR, msg)


@router.patch(
    "/api/v0/graph",
)
async def update_graph(
    body: UpdateRequestBody,
) -> str:
    """Update Distributed Knowledge Graph"""

    timestamps = [
        timestamp["graphURI"]["value"]
        for timestamp in perform_query(timestamps_query, fuseki).results.bindings
    ]

    logger.debug(f"{len(timestamps)} timestamps retrieved now.")

    g = ConjunctiveGraph()
    g.parse(StringIO(dumps(body)), format="json-ld")

    ts = int(time() * 1000)  # current timestamp
    n_triples = 0

    graph_name = ""
    if "@id" in body:
        graph_name = body["@id"]
        if graph_name[-1] != "/":
            graph_name += "/"

    graph_name = '<%stimestamp:%d>' %  (graph_name, ts)

    query, n_triples, graph_name = compose_insert_query_form_graph(g, graph_name)
    
    fuseki.update_query(query)
    logger.debug(
            f"Inserted {n_triples} triple(s) into graph {graph_name}."
        )



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
