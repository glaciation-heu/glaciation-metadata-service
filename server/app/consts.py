from enum import Enum

from app.schemas import ResponseHead, ResponseResults, SearchResponse


class TagEnum(Enum):
    GRAPH = "Graph"
    MONITORING = "Monitoring"


EMPTY_SEARCH_RESPONSE = SearchResponse(
    head=ResponseHead(vars=[]),
    results=ResponseResults(bindings=[]),
)
