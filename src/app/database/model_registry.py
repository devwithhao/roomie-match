from __future__ import annotations

# Importing this module registers every SQLAlchemy model on Base.metadata.
from app.features.chatbot.models.chat_message import ChatMessage
from app.features.chatbot.models.chat_session import ChatSession
from app.features.matching.models.match import UserMatch
from app.features.matching.models.preference import UserPreference
from app.features.matching.models.reject import UserReject
from app.features.packages.models.entitlement import Entitlement
from app.features.packages.models.package import Package
from app.features.packages.models.purchase import Purchase
from app.features.rental_requests.models.rental_history import RentalHistory
from app.features.rooms.models.amenity import Amenity
from app.features.rooms.models.favorite import Favorite
from app.features.rooms.models.post import Post
from app.features.rooms.models.review import Review
from app.features.rooms.models.room import Room
from app.features.rooms.models.room_amenity import RoomAmenity
from app.features.rooms.models.room_image import RoomImage
from app.features.users.models.account import Account
from app.features.users.models.profile import Profile
from app.features.users.models.role import Role

__all__ = [
    "Account",
    "Amenity",
    "ChatMessage",
    "ChatSession",
    "Entitlement",
    "Favorite",
    "Package",
    "Post",
    "Profile",
    "Purchase",
    "RentalHistory",
    "Review",
    "Role",
    "Room",
    "RoomAmenity",
    "RoomImage",
    "UserMatch",
    "UserPreference",
    "UserReject",
]
