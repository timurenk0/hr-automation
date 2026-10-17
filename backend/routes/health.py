from fastapi import APIRouter


router = APIRouter()


@router.get("/api/health")
async def getHealth():
    return { "status": "OK" }