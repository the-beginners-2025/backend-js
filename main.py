import os

import uvicorn
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

import api.admin.router
import api.auth.router
import api.conversations.router
import api.diagrams.router
import api.knowledge.router
import api.ocr.router

load_dotenv()


security = HTTPBasic()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = os.getenv("DOCS_USERNAME")
    correct_password = os.getenv("DOCS_PASSWORD")

    if not correct_username or not correct_password:
        raise RuntimeError(
            "DOCS_USERNAME and DOCS_PASSWORD environment variables not set"
        )

    if not (
        credentials.username == correct_username
        and credentials.password == correct_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return True


def create_app() -> FastAPI:
    app = FastAPI(
        docs_url="/docs" if os.getenv("ENV") == "dev" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if os.getenv("ENV") == "dev" else None,
    )

    if os.getenv("ENV") == "prod":
        from fastapi import APIRouter

        docs_router = APIRouter(dependencies=[Depends(verify_credentials)])

        @docs_router.get("/docs", include_in_schema=False)
        async def get_docs():
            from fastapi.openapi.docs import get_swagger_ui_html

            return get_swagger_ui_html(openapi_url="/openapi.json", title="Docs")

        @docs_router.get("/openapi.json", include_in_schema=False)
        async def get_openapi():
            return app.openapi()

        app.include_router(docs_router)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

    app.include_router(api.auth.router.router)
    app.include_router(api.ocr.router.router)
    app.include_router(api.knowledge.router.router)
    app.include_router(api.conversations.router.router)
    app.include_router(api.diagrams.router.router)
    app.include_router(api.admin.router.router)

    return app


app = create_app()

if __name__ == "__main__":
    if os.getenv("ENV") == "dev":
        uvicorn.run("main:app", host="0.0.0.0", port=9827, reload=True)
    elif os.getenv("ENV") == "prod":
        uvicorn.run("main:app", host="0.0.0.0", port=9826)
    else:
        raise ValueError("ENV must be either 'dev' or 'prod'")
