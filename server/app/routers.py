from typing import Any, Callable

from glob import glob
from json import dump, dumps
from os import getenv, makedirs, path, remove
from re import findall, sub
from time import sleep, time

from fastapi import APIRouter, HTTPException
from loguru import logger
from starlette.responses import RedirectResponse
from starlette.status import (
    HTTP_303_SEE_OTHER,
    HTTP_400_BAD_REQUEST,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.consts import TagEnum
from app.GraphStore import GraphStore
from app.schemas import (
    ResponseHead,
    ResponseResults,
    SearchResponse,
    SPARQLQuery,
    UpdateRequestBody,
    UpdateSPARQLQuery,
)

router = APIRouter(tags=[TagEnum.GRAPH])

STORE_PATH = getenv("STORE_PATH")
_MAX_RETRIES = int(getenv("MAX_RETRIES", "3"))
_RETRY_BASE_DELAY = float(getenv("RETRY_BASE_DELAY", "1.0"))
store = GraphStore(STORE_PATH)

HISTORY_FILES_DIRNAME = "history_files/"
N_HISTORY_FILES = 10
JSON_LD_OUTPUT_FILE = "incoming_json_ld_{timestamp}.jsonld"


def _sparql_with_retry(fn: Callable[[], Any], description: str = "SPARQL") -> Any:
    """Run a GraphStore call with exponential-backoff retries."""
    last_exc: Exception = RuntimeError("unreachable")
    for attempt in range(_MAX_RETRIES):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            if attempt < _MAX_RETRIES - 1:
                delay = _RETRY_BASE_DELAY * (2**attempt)
                logger.warning(
                    f"{description} attempt {attempt + 1}/{_MAX_RETRIES} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                sleep(delay)
    raise last_exc


def cleanup_old_files(directory, pattern, max_files):
    """Keeps only the latest 'max_files' files in 'directory' and deletes older ones."""
    files = sorted(glob(path.join(directory, pattern)), key=path.getmtime, reverse=True)

    if len(files) > max_files:
        for file in files[max_files:]:
            remove(file)
            logger.info(f"Deleted old history file: {file}")


def save_jsonld(data, timestamp):
    fname = HISTORY_FILES_DIRNAME + JSON_LD_OUTPUT_FILE.format(timestamp=timestamp)

    makedirs(HISTORY_FILES_DIRNAME, exist_ok=True)
    with open(fname, "w", encoding="utf-8") as f:
        dump(data, f, indent=4, ensure_ascii=False)
    logger.info(f"Saved JSON-LD into a history file: {fname}")

    pattern = sub(r"\{timestamp\}", "*", JSON_LD_OUTPUT_FILE)
    cleanup_old_files(HISTORY_FILES_DIRNAME, pattern, N_HISTORY_FILES)


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
    ts = int(time() * 1000)  # current timestamp

    graph_name = ""
    if "@id" in body:
        graph_name = body["@id"]
        if graph_name[-1] != "/":
            graph_name += "/"
    graph_name += f"timestamp:{ts}"
    body["@id"] = graph_name

    save_jsonld(body, ts)
    json_ld_str = dumps(body)

    try:
        n_triples = store.ingest_jsonld(json_ld_str)
    except Exception as e:
        logger.exception("Ingest failed")
        raise HTTPException(HTTP_500_INTERNAL_SERVER_ERROR, str(e))

    if n_triples == 0:
        logger.error("No triples could be extracted from JSON-LD.")
        raise HTTPException(
            HTTP_400_BAD_REQUEST, "No triples could be extracted from JSON-LD."
        )

    logger.debug(f"Inserted {n_triples} triple(s) into graph <{graph_name}>.")

    return f"Success - Inserted {n_triples} triple(s) into graph <{graph_name}>."


@router.get(
    "/api/v0/graph",
)
async def search_graph(
    query: SPARQLQuery,
) -> SearchResponse:
    """Execute SPARQL search query and return a response in JSON format."""
    valid, msg = store.validate_sparql(query, "query")

    if valid:
        try:
            result = _sparql_with_retry(lambda: store.read_query(query), "SPARQL read")
            logger.debug(f"Found {len(result['bindings'])} result(s).")
            return SearchResponse(
                head=ResponseHead(vars=result["vars"]),
                results=ResponseResults(bindings=result["bindings"]),
            )
        except Exception as e:
            raise HTTPException(HTTP_500_INTERNAL_SERVER_ERROR, str(e))
    else:
        logger.error(msg)
        logger.debug(f"The query:\n{query}")
        raise HTTPException(HTTP_400_BAD_REQUEST, msg)


def _execute_update_query(query):
    valid, msg = store.validate_sparql(query, "update")

    if valid:
        try:
            _sparql_with_retry(lambda: store.update_query(query), "SPARQL update")
        except Exception as e:
            raise HTTPException(HTTP_500_INTERNAL_SERVER_ERROR, str(e))

        logger.debug(f'Performed "{query}".')
    else:
        logger.error(msg)
        logger.debug(f"The query:\n{query}")
        raise HTTPException(HTTP_400_BAD_REQUEST, msg)


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
        _execute_update_query(single_query)

    return "Success"


@router.post(
    "/api/v0/graph/update",
)
async def perform_post_update_query(
    query: UpdateSPARQLQuery,
) -> str:
    """Execute SPARQL update query and return a response."""

    if "query" not in query or len(query) != 1 or not isinstance(query["query"], str):
        logger.error("Request must contain only {'query': str}")
        raise HTTPException(
            HTTP_400_BAD_REQUEST, "Request must contain only {'query': str}"
        )

    queries = findall(r"DROP GRAPH <.*?>;?", query["query"])
    if len(queries) == 0:
        queries = [query["query"]]

    for single_query in queries:
        _execute_update_query(single_query)

    return "Success"


@router.post(
    "/api/v0/graph/compact",
)
async def perform_compaction() -> str:
    """Optimize the graph store."""
    try:
        store.optimize()
        logger.info("Store optimization completed successfully.")
        return "Success"
    except Exception as e:
        logger.exception("An unexpected error occurred during optimization.")
        raise HTTPException(HTTP_500_INTERNAL_SERVER_ERROR, str(e))
