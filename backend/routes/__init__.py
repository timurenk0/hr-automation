from fastapi import FastAPI
from routes.router import router
from pdf.router import router

# from routes import health


def registerRoutes(app: FastAPI) -> None:
    app.include_router(router, prefix="/api")
