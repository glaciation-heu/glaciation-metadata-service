from json import load

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.status import HTTP_200_OK, HTTP_303_SEE_OTHER, HTTP_400_BAD_REQUEST

from app import routers

app = FastAPI()
app.include_router(routers.router)

client = TestClient(app)


def test__read_root__redirected() -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == HTTP_303_SEE_OTHER
    assert response.text == ""
    assert response.headers["Location"] == "/docs"


def test__update_graph__redirected() -> None:
    with open("app/tests/stub_message.jsonld", "r") as f:
        json_input = load(f)
    response = client.patch(
        "/api/v0/graph",
        json=json_input,
    )
    assert response.status_code == HTTP_200_OK
    assert "Success" in response.json()

    json_input = {"incorrect": "JSON-LD"}
    response = client.patch(
        "/api/v0/graph",
        json=json_input,
    )
    assert response.status_code == HTTP_400_BAD_REQUEST


def test__search_graph__redirected() -> None:
    response = client.get(
        "/api/v0/graph",
        params={
            "query": """
            SELECT ?subject ?predicate ?object
            WHERE {
                ?subject ?predicate ?object
            }
            """
        },
    )
    assert response.status_code == HTTP_200_OK

    response = client.get(
        "/api/v0/graph",
        params={
            "query": """
            SELECT ?subject ?predicate ?object
            WHERE
                ?subject ?predicate ?object
            }
            """
        },
    )
    assert response.status_code == HTTP_400_BAD_REQUEST
