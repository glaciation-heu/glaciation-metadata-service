from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.status import HTTP_200_OK, HTTP_303_SEE_OTHER

from app import routers

app = FastAPI()
app.include_router(routers.router)

client = TestClient(app)


def test__read_root__redirected() -> None:
    response = client.get("/", allow_redirects=False)
    assert response.status_code == HTTP_303_SEE_OTHER
    assert response.text == ""
    assert response.headers["Location"] == "/docs"


def test__update_graph__redirected() -> None:
    response = client.patch("/api/v0/graph", json={"sparql": "PREFIX ns1: <http://dellemc.com:8080/icv/> PREFIX schema: <https://schema.org/> PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> DELETE DATA {  <urn:ngsi-ld:Vehicle:5FSQC8LARN> ns1:driverSeatLocation 'Right'^^schema:steeringPosition .}"})
    assert response.status_code == HTTP_200_OK
    assert response.json() == "Success"
