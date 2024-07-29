from pydantic import BaseModel


class ResposneHead(BaseModel):
    vars: list[str]


class ResponseResults(BaseModel):
    bindings: list[object]


class SearchResponse(BaseModel):
    head: ResposneHead
    results: ResponseResults
