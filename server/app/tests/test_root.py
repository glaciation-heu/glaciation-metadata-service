from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.status import HTTP_303_SEE_OTHER

from .. import root

app = FastAPI()
app.include_router(root.router)

client = TestClient(app)


def test_read() -> None:
    response = client.get("/", allow_redirects=False)
    assert response.status_code == HTTP_303_SEE_OTHER
    assert response.text == ""
    assert response.headers["Location"] == "/docs"
