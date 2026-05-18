from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.auth.routes import router as auth_router
from app.api.v1.rooms.routes import router as rooms_router
from app.api.v1.users.routes import router as users_router
from app.api.v1.packages import router as packages_router
from app.api.v1.packages.webhook import router as packages_webhook_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(rooms_router, prefix="/posts", tags=["posts"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(packages_router, prefix="/packages", tags=["packages"])
api_router.include_router(
    packages_webhook_router, prefix="/packages", tags=["packages"]
)
