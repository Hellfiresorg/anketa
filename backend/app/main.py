import logging  # reload trigger

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.middleware import CorrelationIdMiddleware

settings = get_settings()

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(settings.LOG_LEVEL)),
)

if settings.SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)

app = FastAPI(title="Voice Survey API", version="1.0.0", docs_url="/docs", redoc_url="/redoc")

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.auth import router as auth_router, router_me
from app.api.public import router as public_router
from app.api.invitations import router as invitations_router

app.include_router(auth_router)
app.include_router(router_me)
app.include_router(public_router)
app.include_router(invitations_router)


@app.get("/health", tags=["system"])
async def health():
    from sqlalchemy import text
    from app.db import AsyncSessionLocal
    import redis.asyncio as aioredis

    db_status = "error"
    redis_status = "error"

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        pass

    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        redis_status = "ok"
    except Exception:
        pass

    return {"status": "ok", "db": db_status, "redis": redis_status}


@app.get("/metrics", tags=["system"])
async def metrics():
    return JSONResponse(content="# Prometheus metrics stub\n", media_type="text/plain")
