from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.exception_handlers import error_responses, register_exception_handlers
from routes.router import router


app = FastAPI(
    title="hr-automation",
    responses=error_responses(),
)

register_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    # allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {"message": "hello from backend"}
