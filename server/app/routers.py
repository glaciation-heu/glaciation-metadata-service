from typing import Any, Dict

from io import StringIO
from json import dumps
from time import time

from fastapi import APIRouter, HTTPException
from loguru import logger
from rdflib import BNode, ConjunctiveGraph, Literal, URIRef  # Graph
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

simple_query = """SELECT ?s ?p ?o
WHERE {
  GRAPH <graph1> {
    ?s ?p ?o.
    }
}
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


def compose_insert_query_form_graph(
    g: ConjunctiveGraph, graph_name: str
) -> tuple[str, int]:
    n_triples = 0
    query = "INSERT DATA {\n"
    query += "\tGRAPH <" + graph_name + "> {\n"  # "\tGRAPH <timestamp:%d> {\n" % ts
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
        return query, n_triples
    else:
        logger.error(msg)
        logger.debug(f"The query:\n{query}")
        raise HTTPException(HTTP_500_INTERNAL_SERVER_ERROR, msg)


def find_temp(timestamps):
    for timestamp in timestamps:
        if "temp" in timestamp:
            return timestamp
    return "none"


def find_base(timestamps):
    for timestamp in timestamps:
        if "base" in timestamp:
            return timestamp
    return "no base"


def get_graph_from_bindings(bindings):
    triple_type = {"uri": URIRef, "literal": Literal, "bnode": BNode}

    g = ConjunctiveGraph()

    for binding in bindings:  # response.results.bindings:
        g.add(
            (
                triple_type[binding["s"]["type"]](binding["s"]["value"]),
                triple_type[binding["p"]["type"]](binding["p"]["value"]),
                triple_type[binding["o"]["type"]](binding["o"]["value"]),
            )
        )

    return g


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

    graph_name = ""
    if "@id" in body:
        graph_name = body["@id"]
        if graph_name[-1] != "/":
            graph_name += "/"

    graph_name = "%stimestamp:%d" % (graph_name, ts)

    if len(timestamps) == 0:
        # write the very first graph with a suffix /base
        query, n_triples = compose_insert_query_form_graph(g, graph_name + "/base")

        fuseki.update_query(query)
        logger.debug(
            f"Inserted {n_triples} triple(s) into graph {graph_name}. Base Graph!"
        )
    else:
        # finding previous graph
        timestamp_previous = find_temp(timestamps)
        if timestamp_previous == "none":
            timestamp_previous = find_base(timestamps)
        logger.debug(f"Previous graph was {timestamp_previous}.")

        # reading previous graph
        query_g0 = simple_query.replace("graph1", timestamp_previous)
        response = perform_query(query_g0, fuseki)
        g0 = get_graph_from_bindings(response.results.bindings)

        delta_plus = g - g0
        delta_minus = g0 - g

        query_plus, n_triples_plus = compose_insert_query_form_graph(
            delta_plus, graph_name + "/added"
        )
        query_minus, n_triples_minus = compose_insert_query_form_graph(
            delta_minus, graph_name + "/removed"
        )
        fuseki.update_query(query_plus)
        logger.debug(
            f"Inserted {n_triples_plus} triple(s) into graph {graph_name + '/added'}."
        )
        fuseki.update_query(query_minus)
        logger.debug(
            f"Inserted {n_triples_minus} triple(s) into graph {graph_name+'/removed'} ."
        )
        # remove previous temp graph
        if "temp" in timestamp_previous:
            query_delete = f"DROP GRAPH <{timestamp_previous}>"
            fuseki.update_query(query_delete)
            logger.debug("Removed old temporal")

        # add new temporal graph
        query_temp, n_triples_temp = compose_insert_query_form_graph(
            g, graph_name + "/temp"
        )
        fuseki.update_query(query_temp)

        logger.debug(f"Added new temporal {n_triples_temp} triples")

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
