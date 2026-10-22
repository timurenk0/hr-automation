from fastapi import APIRouter

from pdf.router import router as pdf_router
from routes.health import router as health_router


router = APIRouter(prefix="/api")
router.include_router(pdf_router)
router.include_router(health_router)
