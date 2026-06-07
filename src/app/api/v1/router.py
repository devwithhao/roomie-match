from __future__ import annotations

from fastapi import APIRouter

from app.features.chatbot.routers.chatbot import router as chatbot_router
from app.features.matching.routers.matching import router as matching_router
from app.features.packages.routers.packages import router as packages_router
from app.features.packages.routers.webhook import router as packages_webhook_router
from app.features.rooms.routers.posts import router as posts_router
from app.features.rooms.routers.reviews import router as reviews_router
from app.features.users.routers.auth import router as auth_router
from app.features.users.routers.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(posts_router, prefix="/posts", tags=["posts"])
api_router.include_router(reviews_router, prefix="/rooms", tags=["rooms"])
api_router.include_router(matching_router)
api_router.include_router(packages_router, prefix="/packages", tags=["packages"])
api_router.include_router(packages_webhook_router, prefix="/packages", tags=["packages"])
api_router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])
