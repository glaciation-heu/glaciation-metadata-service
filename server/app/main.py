from typing import Any, Dict

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from prometheus_fastapi_instrumentator import Instrumentator

from app import routers
from app.consts import TagEnum


class CustomFastAPI(FastAPI):
    def openapi(self) -> Dict[str, Any]:
        if self.openapi_schema:
            return self.openapi_schema
        openapi_schema = get_openapi(
            title="GLACIATION Metadata Service",
            version="1.4",  # Same as service version but without minor part
            description=(
                "The service exposes API to work with Distributed Knowledge Graph"
            ),
            license_info={
                "name": "MIT License",
                "url": (
                    "https://github.com/glaciation-heu"
                    "/glaciation-metadata-service/blob/main/LICENSE"
                ),
            },
            routes=self.routes,
        )
        self.openapi_schema = openapi_schema
        return self.openapi_schema


app = CustomFastAPI()
app.include_router(routers.router)


Instrumentator().instrument(app).expose(app, tags=[TagEnum.MONITORING])
