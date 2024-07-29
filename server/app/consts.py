from enum import Enum

from app.schemas import ResponseResults, ResposneHead, SearchResponse


class TagEnum(Enum):
    GRAPH = "Graph"
    MONITORING = "Monitoring"


EMPTY_SEARCH_RESPONSE = SearchResponse(
    head=ResposneHead(vars=[]),
    results=ResponseResults(bindings=[]),
)
