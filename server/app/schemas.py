from typing import Annotated

from fastapi import Query
from pydantic import BaseModel


class ResposneHead(BaseModel):
    vars: list[str]


class ResponseResults(BaseModel):
    bindings: list[object]


class SearchResponse(BaseModel):
    head: ResposneHead
    results: ResponseResults


SPARQLQuery = Annotated[
    str,
    Query(
        description=(
            "Request body must be a SELECT SPARQL query. "
            "It must be compatible with GLACIATION metadata upper ontology."
        ),
    ),
]
