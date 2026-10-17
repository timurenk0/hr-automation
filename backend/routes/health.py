from routes.router import router


@router.get("/health")
async def getHealth():
    return { "status": "OK" }