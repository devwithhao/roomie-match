from __future__ import annotations

from fastapi import APIRouter

from app.features.chatbot.routers.chatbot import router as chatbot_router
from app.features.landlord.router import router as landlord_router
from app.features.matching.routers.matching import router as matching_router
from app.features.packages.routers.packages import router as packages_router
from app.features.packages.routers.webhook import router as packages_webhook_router
from app.features.packages.routers.vnpay import router as vnpay_router
from app.features.rooms.routers.posts import router as posts_router
from app.features.rooms.routers.reviews import router as reviews_router
from app.features.users.routers.auth import router as auth_router
from app.features.users.routers.users import router as users_router
from app.features.users.routers.contact import router as contact_router
from app.features.admin.routers.users import router as admin_users_router
from app.features.admin.routers.packages import router as admin_packages_router
from app.features.admin.routers.role_features import router as admin_role_features_router
from app.features.admin.routers.moderation import router as admin_moderation_router
from app.features.admin.routers.analytics import router as admin_analytics_router
from app.features.admin.routers.orders import router as admin_orders_router
from app.features.admin.routers.categories import router as admin_categories_router
from app.features.admin.routers.complaints import router as admin_complaints_router
from app.shared.routers.upload import router as upload_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["auth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(contact_router, prefix="/contact", tags=["contact"])
api_router.include_router(admin_users_router, prefix="/admin", tags=["admin-users"])
api_router.include_router(landlord_router, prefix="/landlord", tags=["landlord"])
api_router.include_router(admin_packages_router, prefix="/admin/packages", tags=["admin-packages"])
api_router.include_router(admin_role_features_router, prefix="/admin/role-features", tags=["admin-role-features"])
api_router.include_router(admin_moderation_router, prefix="/admin", tags=["admin-moderation"])
api_router.include_router(admin_analytics_router, prefix="/admin", tags=["admin-analytics"])
api_router.include_router(admin_orders_router, prefix="/admin/orders", tags=["admin-orders"])
api_router.include_router(admin_categories_router, prefix="/admin/categories", tags=["admin-categories"])
api_router.include_router(admin_complaints_router, prefix="/admin/complaints", tags=["admin-complaints"])
api_router.include_router(posts_router, prefix="/posts", tags=["posts"])
api_router.include_router(reviews_router, prefix="/rooms", tags=["rooms"])
api_router.include_router(matching_router)
api_router.include_router(packages_router, prefix="/packages", tags=["packages"])
api_router.include_router(packages_webhook_router, prefix="/packages", tags=["packages"])
api_router.include_router(vnpay_router, prefix="/payments/vnpay", tags=["payments"])
api_router.include_router(chatbot_router, prefix="/chatbot", tags=["chatbot"])
api_router.include_router(upload_router, prefix="/upload", tags=["upload"])
