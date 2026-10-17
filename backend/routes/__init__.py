from fastapi import FastAPI
from routes.router import router
from routes import health, upload_pdf


def registerRoutes(app: FastAPI) -> None:
    app.include_router(router, prefix="/api")