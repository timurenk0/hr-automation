from fastapi import FastAPI
from routes.health import router as health_router


def registerRoutes(app: FastAPI):
    app.include_router(health_router)