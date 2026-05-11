from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth.routes import router as auth_router
from app.api.v1.rooms.routes import router as rooms_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(rooms_router, prefix="/posts", tags=["posts"])

