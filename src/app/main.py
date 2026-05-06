from __future__ import annotations

from fastapi import FastAPI

from app.api.v1.router import api_router

app = FastAPI(title="RoomieMatch API", version="1.0.0")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "RoomieMatch API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router, prefix="/api/v1")
