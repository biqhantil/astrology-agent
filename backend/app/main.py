"""FastAPI application factory and root-level routes."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import db
from app.routers import auth, birth_profiles, charts, life_phases, me, synastry, transits

# ── Lifespan ─────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: connect to Postgres + Redis. Shutdown: close connections."""
    # Startup
    await db.connect()
    yield
    # Shutdown
    await db.disconnect()


# ── App Factory ──────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health Endpoint ──────────────────────────────────────────────

@app.get("/v1/health", tags=["system"])
async def health_check(request: Request) -> dict:
    """Return system health status.

    Checks database connectivity and returns basic service metadata.
    """
    db_ok = await db.check_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "version": settings.APP_VERSION,
        "database": "connected" if db_ok else "disconnected",
    }


# ── Routers ────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
app.include_router(me.router, prefix="/v1/me", tags=["me"])
app.include_router(birth_profiles.router, prefix="/v1/me/profile", tags=["birth-profiles"])
app.include_router(birth_profiles.router, prefix="/v1/me/birth-profile", tags=["birth-profiles"], include_in_schema=False)
app.include_router(synastry.router, prefix="/v1/synastry", tags=["synastry"])
app.include_router(transits.router, prefix="/v1/charts", tags=["transits"])
app.include_router(charts.router, prefix="/v1/charts", tags=["charts"])
app.include_router(life_phases.router, prefix="/v1", tags=["life-phases"])

# Remaining routers wired in later chunks:
# from app.routers import conversations, stream
# app.include_router(conversations.router, prefix="/v1/conversations", tags=["conversations"])
# app.include_router(stream.router, prefix="/v1/stream", tags=["stream"])
