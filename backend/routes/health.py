from fastapi import APIRouter


router = APIRouter(tags=["Health"])


@router.get("/health")
async def getHealth():
    return {"status": "OK"}
