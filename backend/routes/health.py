from fastapi import APIRouter


router = APIRouter()


@router("/api/health")
async def getHealth():
    return { "status": "OK" }