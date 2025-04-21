import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import api.auth.router
import api.ocr.router

load_dotenv()


def create_app() -> FastAPI:
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api.auth.router.router)
    app.include_router(api.ocr.router.router)

    return app


app = create_app()

if __name__ == "__main__":
    if os.getenv("ENV") == "dev":
        uvicorn.run("main:app", host="0.0.0.0", port=9827, reload=True)
    elif os.getenv("ENV") == "prod":
        uvicorn.run("main:app", host="0.0.0.0", port=9826)
    else:
        raise ValueError("ENV must be either 'dev' or 'prod'")
