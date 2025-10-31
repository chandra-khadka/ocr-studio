import time

from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import api_router
from backend.core.config import settings

app = FastAPI(title=settings.APP_NAME, version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Response time header
@app.middleware("http")
async def add_timing(request: Request, call_next):
    start = time.time()
    resp = await call_next(request)
    resp.headers["X-Response-Time-ms"] = f"{(time.time() - start) * 1000:.2f}"
    return resp


# API
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", include_in_schema=False)
def root():
    return {"message": f"{settings.APP_NAME} — see {settings.API_V1_PREFIX}/docs"}
