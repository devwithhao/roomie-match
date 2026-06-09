from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.database.model_registry  # noqa: F401
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.features.chatbot.models.chat_message import ChatMessage
from app.features.chatbot.models.chat_session import ChatSession
from app.features.matching.models.match import UserMatch
from app.features.matching.models.preference import UserPreference
from app.features.matching.models.reject import UserReject
from app.features.packages.models import Entitlement, Package, Purchase
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

DEFAULT_PASSWORD = "password123"


def get_or_create_role(db: Session, name: str, description: str) -> Role:
    role = db.scalar(select(Role).where(Role.name == name))
    if role is None:
        role = Role(name=name, description=description)
        db.add(role)
        db.flush()
    else:
        role.description = description
    return role


def get_or_create_account(
    db: Session,
    *,
    email: str,
    username: str,
    role: Role,
    full_name: str,
    phone: str | None = None,
    gender: str | None = None,
    avatar_url: str | None = None,
    facebook: str | None = None,
    instagram: str | None = None,
) -> Account:
    account = db.scalar(select(Account).where(Account.email == email))
    if account is None:
        account = Account(
            email=email,
            username=username,
            password_hash=hash_password(DEFAULT_PASSWORD),
            role_id=role.id,
            email_verified=True,
            status="active",
        )
        db.add(account)
        db.flush()
    else:
        account.username = username
        account.role_id = role.id
        account.email_verified = True
        account.status = "active"
        if not account.password_hash:
            account.password_hash = hash_password(DEFAULT_PASSWORD)

    profile = db.get(Profile, account.id)
    if profile is None:
        profile = Profile(account_id=account.id, full_name=full_name)
        db.add(profile)
    profile.full_name = full_name
    profile.phone = phone
    profile.gender = gender
    profile.avatar_url = avatar_url
    profile.facebook = facebook
    profile.instagram = instagram
    return account


def get_or_create_amenity(db: Session, name: str, category: str) -> Amenity:
    amenity = db.scalar(select(Amenity).where(Amenity.name == name))
    if amenity is None:
        amenity = Amenity(name=name, category=category)
        db.add(amenity)
        db.flush()
    else:
        amenity.category = category
    return amenity


def attach_amenity(db: Session, room: Room, amenity: Amenity) -> None:
    exists = db.get(RoomAmenity, {"room_id": room.id, "amenity_id": amenity.id})
    if exists is None:
        db.add(RoomAmenity(room_id=room.id, amenity_id=amenity.id))


def ensure_room_image(db: Session, room: Room, image_url: str) -> None:
    exists = db.scalar(
        select(RoomImage).where(
            RoomImage.room_id == room.id,
            RoomImage.image_url == image_url,
        )
    )
    if exists is None:
        db.add(RoomImage(room_id=room.id, image_url=image_url))


def get_or_create_room_with_post(
    db: Session,
    *,
    landlord: Account,
    data: dict,
    amenities: list[Amenity],
) -> tuple[Room, Post]:
    room = db.scalar(
        select(Room).where(Room.account_id == landlord.id, Room.title == data["title"])
    )
    if room is None:
        room = Room(account_id=landlord.id, title=data["title"])
        db.add(room)
        db.flush()

    room.room_type = data["room_type"]
    room.area = data["area"]
    room.max_people = data["max_people"]
    room.current_people = data["current_people"]
    room.bedroom_count = data["bedroom_count"]
    room.description = data["description"]
    room.city = data["city"]
    room.district = data["district"]
    room.ward = data["ward"]
    room.street = data["street"]
    room.full_address = data["full_address"]
    room.latitude = data["latitude"]
    room.longitude = data["longitude"]
    room.price = data["price"]
    room.electricity_price = data["electricity_price"]
    room.water_price = data["water_price"]
    room.internet_price = data["internet_price"]
    room.parking_price = data["parking_price"]
    room.deposit = data["deposit"]
    room.status = "available"
    room.contact_name = data["contact_name"]
    room.contact_phone = data["contact_phone"]
    room.contact_social = data["contact_social"]

    for amenity in amenities:
        attach_amenity(db, room, amenity)
    for image_url in data["images"]:
        ensure_room_image(db, room, image_url)

    post = db.scalar(select(Post).where(Post.room_id == room.id))
    if post is None:
        post = Post(room_id=room.id, account_id=landlord.id)
        db.add(post)
        db.flush()
    post.account_id = landlord.id
    post.status = "active"
    post.is_vip = data["is_vip"]
    return room, post


def get_or_create_package(
    db: Session,
    *,
    slug: str,
    name: str,
    description: str,
    price_cents: int,
    credits_match: int,
    credits_chatbot: int,
    period: str,
    features: list[str],
) -> Package:
    package = db.scalar(select(Package).where(Package.slug == slug))
    if package is None:
        package = Package(slug=slug)
        db.add(package)

    package.name = name
    package.description = description
    package.price_cents = price_cents
    package.currency = "vnd"
    package.credits_match = credits_match
    package.credits_chatbot = credits_chatbot
    package.period = period
    package.features = features
    package.active = True
    db.flush()
    return package


def ensure_favorite(db: Session, account: Account, post: Post) -> None:
    exists = db.get(Favorite, {"account_id": account.id, "post_id": post.id})
    if exists is None:
        db.add(Favorite(account_id=account.id, post_id=post.id))


def ensure_rental_history(
    db: Session,
    *,
    account: Account,
    room: Room,
    post: Post,
    start_date: date,
    end_date: date | None,
    status: str,
) -> None:
    exists = db.scalar(
        select(RentalHistory).where(
            RentalHistory.account_id == account.id,
            RentalHistory.room_id == room.id,
            RentalHistory.post_id == post.id,
            RentalHistory.start_date == start_date,
        )
    )
    if exists is None:
        db.add(
            RentalHistory(
                account_id=account.id,
                room_id=room.id,
                post_id=post.id,
                start_date=start_date,
                end_date=end_date,
                status=status,
            )
        )
    else:
        exists.end_date = end_date
        exists.status = status


def ensure_review(
    db: Session,
    *,
    account: Account,
    room: Room,
    rating: int,
    comment: str,
) -> None:
    exists = db.scalar(
        select(Review).where(
            Review.account_id == account.id,
            Review.room_id == room.id,
        )
    )
    if exists is None:
        db.add(
            Review(
                account_id=account.id,
                room_id=room.id,
                rating=rating,
                comment=comment,
            )
        )
    else:
        exists.rating = rating
        exists.comment = comment


def ensure_preference(
    db: Session,
    *,
    account: Account,
    budget_min: int,
    budget_max: int,
    target_city: str,
    target_district: str,
    target_gender: str | None,
    habit: list[str],
    introduce: str,
    suggested_accounts: list[int],
) -> UserPreference:
    preference = db.get(UserPreference, account.id)
    if preference is None:
        preference = UserPreference(account_id=account.id)
        db.add(preference)
        db.flush()

    preference.budget_min = budget_min
    preference.budget_max = budget_max
    preference.target_city = target_city
    preference.target_district = target_district
    preference.target_gender = target_gender
    preference.habit = habit
    preference.introduce = introduce
    preference.suggested_accounts = suggested_accounts
    return preference


def ensure_match(db: Session, account_1: Account, account_2: Account) -> None:
    first_id, second_id = sorted((account_1.id, account_2.id))
    exists = db.get(UserMatch, {"account_id_1": first_id, "account_id_2": second_id})
    if exists is None:
        db.add(
            UserMatch(
                account_id_1=first_id,
                account_id_2=second_id,
                is_matched=True,
            )
        )
    else:
        exists.is_matched = True


def ensure_reject(db: Session, account: Account, rejected_account: Account) -> None:
    exists = db.get(
        UserReject,
        {
            "account_id": account.id,
            "rejected_account_id": rejected_account.id,
        },
    )
    if exists is None:
        db.add(
            UserReject(
                account_id=account.id,
                rejected_account_id=rejected_account.id,
            )
        )


def ensure_purchase(
    db: Session,
    *,
    account: Account,
    package: Package,
    provider_payment_id: str,
    status: str,
) -> Purchase:
    purchase = db.scalar(
        select(Purchase).where(
            Purchase.provider == "sample",
            Purchase.provider_payment_id == provider_payment_id,
        )
    )
    if purchase is None:
        purchase = Purchase(
            account_id=account.id,
            package_id=package.id,
            provider="sample",
            provider_payment_id=provider_payment_id,
            amount_cents=package.price_cents,
            currency=package.currency,
            status=status,
            raw_payload={"seed": True, "provider_payment_id": provider_payment_id},
        )
        db.add(purchase)
        db.flush()
    else:
        purchase.account_id = account.id
        purchase.package_id = package.id
        purchase.amount_cents = package.price_cents
        purchase.currency = package.currency
        purchase.status = status
        purchase.raw_payload = {"seed": True, "provider_payment_id": provider_payment_id}
    return purchase


def ensure_entitlement(
    db: Session,
    *,
    account: Account,
    feature_key: str,
    quantity: int | None,
    source_purchase: Purchase,
    expires_at: datetime | None = None,
) -> None:
    entitlement = db.scalar(
        select(Entitlement).where(
            Entitlement.account_id == account.id,
            Entitlement.feature_key == feature_key,
            Entitlement.source_purchase_id == source_purchase.id,
        )
    )
    if entitlement is None:
        db.add(
            Entitlement(
                account_id=account.id,
                feature_key=feature_key,
                quantity=quantity,
                expires_at=expires_at,
                source_purchase_id=source_purchase.id,
            )
        )
    else:
        entitlement.quantity = quantity
        entitlement.expires_at = expires_at


def ensure_chat_session(
    db: Session,
    *,
    account: Account,
    title: str,
    messages: list[tuple[str, str]],
) -> ChatSession:
    session = db.scalar(
        select(ChatSession).where(
            ChatSession.user_id == account.id,
            ChatSession.title == title,
        )
    )
    if session is None:
        session = ChatSession(user_id=account.id, title=title)
        db.add(session)
        db.flush()

    for role, content in messages:
        exists = db.scalar(
            select(ChatMessage).where(
                ChatMessage.session_id == session.id,
                ChatMessage.role == role,
                ChatMessage.content == content,
            )
        )
        if exists is None:
            db.add(ChatMessage(session_id=session.id, role=role, content=content))
    return session


def create_accounts(db: Session) -> tuple[dict[str, Role], list[Account], list[Account], Account]:
    roles = {
        "tenant": get_or_create_role(db, "tenant", "Nguoi thue tro"),
        "landlord": get_or_create_role(db, "landlord", "Chu tro"),
        "admin": get_or_create_role(db, "admin", "Quan tri he thong"),
    }

    admin = get_or_create_account(
        db,
        email="admin.demo@example.com",
        username="admin_demo",
        role=roles["admin"],
        full_name="Admin Demo",
        phone="0900000099",
        gender="other",
        avatar_url="https://api.dicebear.com/8.x/initials/svg?seed=Admin%20Demo",
    )

    landlords = [
        get_or_create_account(
            db,
            email="landlord.demo@example.com",
            username="landlord_demo",
            role=roles["landlord"],
            full_name="Nguyễn Minh Chủ",
            phone="0900000000",
            gender="male",
            avatar_url="https://api.dicebear.com/8.x/initials/svg?seed=Nguyen%20Minh%20Chu",
            facebook="https://facebook.com/landlord.demo",
        ),
        get_or_create_account(
            db,
            email="landlord.dongnai@example.com",
            username="landlord_dongnai",
            role=roles["landlord"],
            full_name="Trần Lan Chủ",
            phone="0900000010",
            gender="female",
            avatar_url="https://api.dicebear.com/8.x/initials/svg?seed=Tran%20Lan%20Chu",
            facebook="https://facebook.com/landlord.dongnai",
        ),
    ]

    tenant_specs = [
        ("tenant.demo@example.com", "tenant_demo", "Lê An Nhiên", "female"),
        ("tenant01.demo@example.com", "tenant01_demo", "Phạm Hoàng Nam", "male"),
        ("tenant02.demo@example.com", "tenant02_demo", "Võ Minh Anh", "female"),
        ("tenant03.demo@example.com", "tenant03_demo", "Đặng Quốc Bảo", "male"),
        ("tenant04.demo@example.com", "tenant04_demo", "Bùi Thanh Mai", "female"),
        ("tenant05.demo@example.com", "tenant05_demo", "Ngô Gia Huy", "male"),
        ("tenant06.demo@example.com", "tenant06_demo", "Đỗ Khánh Linh", "female"),
        ("tenant07.demo@example.com", "tenant07_demo", "Huỳnh Nhật Minh", "male"),
        ("tenant08.demo@example.com", "tenant08_demo", "Mai Phương Thảo", "female"),
        ("tenant09.demo@example.com", "tenant09_demo", "Cao Đức Tín", "male"),
    ]
    tenants = [
        get_or_create_account(
            db,
            email=email,
            username=username,
            role=roles["tenant"],
            full_name=full_name,
            phone=f"09100000{index:02d}",
            gender=gender,
            avatar_url=f"https://api.dicebear.com/8.x/initials/svg?seed={username}",
            instagram=f"https://instagram.com/{username}",
        )
        for index, (email, username, full_name, gender) in enumerate(tenant_specs, start=1)
    ]
    return roles, landlords, tenants, admin


def create_amenities(db: Session) -> dict[str, Amenity]:
    specs = [
        ("Wifi", "utility"),
        ("Máy lạnh", "utility"),
        ("Chỗ để xe", "utility"),
        ("Máy giặt", "utility"),
        ("Ban công", "space"),
        ("Cửa sổ", "space"),
        ("Bếp riêng", "kitchen"),
        ("Nhà vệ sinh riêng", "bathroom"),
        ("Thang máy", "building"),
        ("Bảo vệ", "building"),
        ("Giờ giấc tự do", "policy"),
        ("Cho nuôi thú cưng", "policy"),
    ]
    return {name: get_or_create_amenity(db, name, category) for name, category in specs}


def create_rooms_and_posts(
    db: Session,
    *,
    landlords: list[Account],
    amenities: dict[str, Amenity],
) -> tuple[list[Room], list[Post]]:
    room_specs = [
        {
            "title": "Studio sáng gần phố đi bộ Nguyễn Huệ",
            "room_type": "studio",
            "area": 28.0,
            "max_people": 2,
            "current_people": 0,
            "bedroom_count": 1,
            "description": "Studio đầy đủ nội thất, đi bộ ra trung tâm Quận 1.",
            "city": "Thành Phố Hồ Chí Minh",
            "district": "Quận 1",
            "ward": "Phường Bến Nghé",
            "street": "Đường Nguyễn Huệ",
            "full_address": "42 Đường Nguyễn Huệ, Phường Bến Nghé, Quận 1, Thành Phố Hồ Chí Minh",
            "latitude": 10.7741,
            "longitude": 106.7038,
            "price": 7800000,
            "electricity_price": 4000,
            "water_price": 120000,
            "internet_price": 100000,
            "parking_price": 200000,
            "deposit": 7800000,
            "contact_name": "Nguyễn Minh Chủ",
            "contact_phone": "0900000000",
            "contact_social": "zalo:0900000000",
            "is_vip": True,
            "amenities": ["Wifi", "Máy lạnh", "Thang máy", "Bảo vệ"],
            "images": [
                "https://images.unsplash.com/photo-1522708323590-d24dbb6b0267",
                "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85",
            ],
        },
        {
            "title": "Phòng ban công khu D2 Bình Thạnh",
            "room_type": "phong_tro",
            "area": 24.0,
            "max_people": 2,
            "current_people": 1,
            "bedroom_count": 1,
            "description": "Phòng thoáng, gần trường Hutech và bến xe buýt.",
            "city": "Thành Phố Hồ Chí Minh",
            "district": "Quận Bình Thạnh",
            "ward": "Phường 25",
            "street": "Đường D2",
            "full_address": "18 Đường D2, Phường 25, Quận Bình Thạnh, Thành Phố Hồ Chí Minh",
            "latitude": 10.8018,
            "longitude": 106.7144,
            "price": 5200000,
            "electricity_price": 3800,
            "water_price": 100000,
            "internet_price": 80000,
            "parking_price": 150000,
            "deposit": 5200000,
            "contact_name": "Nguyễn Minh Chủ",
            "contact_phone": "0900000000",
            "contact_social": "zalo:0900000000",
            "is_vip": False,
            "amenities": ["Wifi", "Ban công", "Máy giặt", "Chỗ để xe"],
            "images": [
                "https://images.unsplash.com/photo-1484154218962-a197022b5858",
                "https://images.unsplash.com/photo-1560448204-e02f11c3d0e2",
            ],
        },
        {
            "title": "Căn hộ mini gần Đại học Quốc Gia",
            "room_type": "can_ho_mini",
            "area": 32.0,
            "max_people": 3,
            "current_people": 0,
            "bedroom_count": 1,
            "description": "Căn hộ mini yên tĩnh, phù hợp sinh viên và người đi làm.",
            "city": "Thành Phố Hồ Chí Minh",
            "district": "Thành phố Thủ Đức",
            "ward": "Phường Linh Trung",
            "street": "Đường số 8",
            "full_address": "123 Đường số 8, Phường Linh Trung, Thành phố Thủ Đức, Thành Phố Hồ Chí Minh",
            "latitude": 10.8701,
            "longitude": 106.8031,
            "price": 4300000,
            "electricity_price": 3500,
            "water_price": 90000,
            "internet_price": 70000,
            "parking_price": 100000,
            "deposit": 4300000,
            "contact_name": "Nguyễn Minh Chủ",
            "contact_phone": "0900000000",
            "contact_social": "zalo:0900000000",
            "is_vip": True,
            "amenities": ["Wifi", "Máy lạnh", "Bếp riêng", "Nhà vệ sinh riêng"],
            "images": [
                "https://images.unsplash.com/photo-1493809842364-78817add7ffb",
                "https://images.unsplash.com/photo-1513694203232-719a280e022f",
            ],
        },
        {
            "title": "Phòng cao cấp gần Crescent Mall Quận 7",
            "room_type": "studio",
            "area": 30.0,
            "max_people": 2,
            "current_people": 0,
            "bedroom_count": 1,
            "description": "Khu an ninh, nội thất mới, gần Phú Mỹ Hưng.",
            "city": "Thành Phố Hồ Chí Minh",
            "district": "Quận 7",
            "ward": "Phường Tân Phú",
            "street": "Đường Nguyễn Lương Bằng",
            "full_address": "36 Đường Nguyễn Lương Bằng, Phường Tân Phú, Quận 7, Thành Phố Hồ Chí Minh",
            "latitude": 10.7291,
            "longitude": 106.7191,
            "price": 6900000,
            "electricity_price": 4000,
            "water_price": 120000,
            "internet_price": 100000,
            "parking_price": 200000,
            "deposit": 6900000,
            "contact_name": "Nguyễn Minh Chủ",
            "contact_phone": "0900000000",
            "contact_social": "zalo:0900000000",
            "is_vip": False,
            "amenities": ["Wifi", "Máy lạnh", "Thang máy", "Bảo vệ", "Chỗ để xe"],
            "images": [
                "https://images.unsplash.com/photo-1560448075-bb485b067938",
                "https://images.unsplash.com/photo-1560448205-4d9b3e6bb6db",
            ],
        },
        {
            "title": "Phòng gác lửng gần Công viên Gia Định",
            "room_type": "phong_tro",
            "area": 22.0,
            "max_people": 2,
            "current_people": 0,
            "bedroom_count": 1,
            "description": "Phòng có gác, khu dân cư yên tĩnh, giờ giấc tự do.",
            "city": "Thành Phố Hồ Chí Minh",
            "district": "Quận Gò Vấp",
            "ward": "Phường 3",
            "street": "Đường Nguyễn Thái Sơn",
            "full_address": "84 Đường Nguyễn Thái Sơn, Phường 3, Quận Gò Vấp, Thành Phố Hồ Chí Minh",
            "latitude": 10.8174,
            "longitude": 106.6792,
            "price": 3900000,
            "electricity_price": 3500,
            "water_price": 80000,
            "internet_price": 60000,
            "parking_price": 100000,
            "deposit": 3900000,
            "contact_name": "Nguyễn Minh Chủ",
            "contact_phone": "0900000000",
            "contact_social": "zalo:0900000000",
            "is_vip": False,
            "amenities": ["Wifi", "Cửa sổ", "Chỗ để xe", "Giờ giấc tự do"],
            "images": [
                "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688",
                "https://images.unsplash.com/photo-1536376072261-38c75010e6c9",
            ],
        },
        {
            "title": "Phòng tiện nghi gần sân bay Tân Sơn Nhất",
            "room_type": "can_ho_mini",
            "area": 26.0,
            "max_people": 2,
            "current_people": 0,
            "bedroom_count": 1,
            "description": "Di chuyển thuận tiện, có thang máy và bảo vệ.",
            "city": "Thành Phố Hồ Chí Minh",
            "district": "Quận Tân Bình",
            "ward": "Phường 2",
            "street": "Đường Bạch Đằng",
            "full_address": "55 Đường Bạch Đằng, Phường 2, Quận Tân Bình, Thành Phố Hồ Chí Minh",
            "latitude": 10.8132,
            "longitude": 106.6655,
            "price": 5600000,
            "electricity_price": 3900,
            "water_price": 100000,
            "internet_price": 90000,
            "parking_price": 150000,
            "deposit": 5600000,
            "contact_name": "Nguyễn Minh Chủ",
            "contact_phone": "0900000000",
            "contact_social": "zalo:0900000000",
            "is_vip": True,
            "amenities": ["Wifi", "Máy lạnh", "Thang máy", "Bảo vệ"],
            "images": [
                "https://images.unsplash.com/photo-1554995207-c18c203602cb",
                "https://images.unsplash.com/photo-1560185893-a55cbc8c57e8",
            ],
        },
        {
            "title": "Phòng mới trung tâm Biên Hòa",
            "room_type": "phong_tro",
            "area": 25.0,
            "max_people": 2,
            "current_people": 0,
            "bedroom_count": 1,
            "description": "Phòng mới xây, gần Vincom Biên Hòa và chợ đêm.",
            "city": "Đồng Nai",
            "district": "Thành phố Biên Hòa",
            "ward": "Phường Tân Mai",
            "street": "Đường Đồng Khởi",
            "full_address": "27 Đường Đồng Khởi, Phường Tân Mai, Thành phố Biên Hòa, Đồng Nai",
            "latitude": 10.9574,
            "longitude": 106.8427,
            "price": 3200000,
            "electricity_price": 3500,
            "water_price": 80000,
            "internet_price": 70000,
            "parking_price": 80000,
            "deposit": 3200000,
            "contact_name": "Trần Lan Chủ",
            "contact_phone": "0900000010",
            "contact_social": "zalo:0900000010",
            "is_vip": False,
            "amenities": ["Wifi", "Cửa sổ", "Chỗ để xe", "Máy giặt"],
            "images": [
                "https://images.unsplash.com/photo-1560185127-6ed189bf02f4",
                "https://images.unsplash.com/photo-1560185007-cde436f6a4d0",
            ],
        },
        {
            "title": "Studio gần khu công nghiệp Long Thành",
            "room_type": "studio",
            "area": 27.0,
            "max_people": 2,
            "current_people": 0,
            "bedroom_count": 1,
            "description": "Phù hợp kỹ sư, chuyên viên làm việc tại Long Thành.",
            "city": "Đồng Nai",
            "district": "Huyện Long Thành",
            "ward": "Thị trấn Long Thành",
            "street": "Đường Lê Duẩn",
            "full_address": "64 Đường Lê Duẩn, Thị trấn Long Thành, Huyện Long Thành, Đồng Nai",
            "latitude": 10.7896,
            "longitude": 106.9491,
            "price": 3800000,
            "electricity_price": 3600,
            "water_price": 90000,
            "internet_price": 70000,
            "parking_price": 100000,
            "deposit": 3800000,
            "contact_name": "Trần Lan Chủ",
            "contact_phone": "0900000010",
            "contact_social": "zalo:0900000010",
            "is_vip": True,
            "amenities": ["Wifi", "Máy lạnh", "Bếp riêng", "Chỗ để xe"],
            "images": [
                "https://images.unsplash.com/photo-1560184897-ae75f418493e",
                "https://images.unsplash.com/photo-1560185008-b033106af5c3",
            ],
        },
        {
            "title": "Phòng rộng gần khu Nhơn Trạch",
            "room_type": "phong_tro",
            "area": 29.0,
            "max_people": 3,
            "current_people": 1,
            "bedroom_count": 1,
            "description": "Phòng rộng, có bếp riêng, thuận tiện đi làm khu công nghiệp.",
            "city": "Đồng Nai",
            "district": "Huyện Nhơn Trạch",
            "ward": "Xã Phước Thiền",
            "street": "Đường Tôn Đức Thắng",
            "full_address": "91 Đường Tôn Đức Thắng, Xã Phước Thiền, Huyện Nhơn Trạch, Đồng Nai",
            "latitude": 10.7245,
            "longitude": 106.8835,
            "price": 3000000,
            "electricity_price": 3500,
            "water_price": 80000,
            "internet_price": 60000,
            "parking_price": 80000,
            "deposit": 3000000,
            "contact_name": "Trần Lan Chủ",
            "contact_phone": "0900000010",
            "contact_social": "zalo:0900000010",
            "is_vip": False,
            "amenities": ["Wifi", "Bếp riêng", "Nhà vệ sinh riêng", "Chỗ để xe"],
            "images": [
                "https://images.unsplash.com/photo-1560185009-dddeb820c7b7",
                "https://images.unsplash.com/photo-1505693416388-ac5ce068fe85",
            ],
        },
        {
            "title": "Căn hộ mini Trảng Bom có ban công",
            "room_type": "can_ho_mini",
            "area": 31.0,
            "max_people": 2,
            "current_people": 0,
            "bedroom_count": 1,
            "description": "Không gian sáng, ban công thoáng, gần Quốc lộ 1A.",
            "city": "Đồng Nai",
            "district": "Huyện Trảng Bom",
            "ward": "Thị trấn Trảng Bom",
            "street": "Đường 3 Tháng 2",
            "full_address": "12 Đường 3 Tháng 2, Thị trấn Trảng Bom, Huyện Trảng Bom, Đồng Nai",
            "latitude": 10.9512,
            "longitude": 107.0058,
            "price": 3500000,
            "electricity_price": 3500,
            "water_price": 90000,
            "internet_price": 70000,
            "parking_price": 80000,
            "deposit": 3500000,
            "contact_name": "Trần Lan Chủ",
            "contact_phone": "0900000010",
            "contact_social": "zalo:0900000010",
            "is_vip": False,
            "amenities": ["Wifi", "Ban công", "Máy lạnh", "Cho nuôi thú cưng"],
            "images": [
                "https://images.unsplash.com/photo-1560440021-33f9b867899d",
                "https://images.unsplash.com/photo-1560185007-5f0bb1866cab",
            ],
        },
    ]

    rooms: list[Room] = []
    posts: list[Post] = []
    for index, spec in enumerate(room_specs):
        landlord = landlords[0] if index < 6 else landlords[1]
        room_amenities = [amenities[name] for name in spec["amenities"]]
        room_data = {key: value for key, value in spec.items() if key != "amenities"}
        room, post = get_or_create_room_with_post(
            db,
            landlord=landlord,
            data=room_data,
            amenities=room_amenities,
        )
        rooms.append(room)
        posts.append(post)

    return rooms, posts


def create_engagement_data(
    db: Session,
    *,
    tenants: list[Account],
    rooms: list[Room],
    posts: list[Post],
) -> None:
    for index, tenant in enumerate(tenants):
        ensure_favorite(db, tenant, posts[index % len(posts)])
        ensure_favorite(db, tenant, posts[(index + 3) % len(posts)])

        ensure_review(
            db,
            account=tenant,
            room=rooms[index % len(rooms)],
            rating=(index % 5) + 1,
            comment=f"Phòng sạch, vị trí tiện đi lại cho nhu cầu số {index + 1}.",
        )

    ensure_rental_history(
        db,
        account=tenants[0],
        room=rooms[0],
        post=posts[0],
        start_date=date(2025, 9, 1),
        end_date=None,
        status="active",
    )
    ensure_rental_history(
        db,
        account=tenants[1],
        room=rooms[2],
        post=posts[2],
        start_date=date(2025, 1, 10),
        end_date=date(2025, 12, 31),
        status="completed",
    )
    ensure_rental_history(
        db,
        account=tenants[2],
        room=rooms[6],
        post=posts[6],
        start_date=date(2026, 2, 15),
        end_date=None,
        status="active",
    )


def create_matching_data(db: Session, *, tenants: list[Account]) -> None:
    for index, tenant in enumerate(tenants):
        suggested = [
            other.id
            for other in tenants
            if other.id != tenant.id
        ][:5]
        city = "Thành Phố Hồ Chí Minh" if index < 6 else "Đồng Nai"
        district = [
            "Quận 1",
            "Quận Bình Thạnh",
            "Thành phố Thủ Đức",
            "Quận 7",
            "Quận Gò Vấp",
            "Quận Tân Bình",
            "Thành phố Biên Hòa",
            "Huyện Long Thành",
            "Huyện Nhơn Trạch",
            "Huyện Trảng Bom",
        ][index]
        ensure_preference(
            db,
            account=tenant,
            budget_min=2500000 + index * 200000,
            budget_max=6500000 + index * 250000,
            target_city=city,
            target_district=district,
            target_gender=None,
            habit=["quiet", "clean", "early_sleep"] if index % 2 == 0 else ["social", "cooking"],
            introduce=f"Mình đang tìm phòng tại {district}, ưu tiên khu an toàn và dễ di chuyển.",
            suggested_accounts=suggested,
        )

    ensure_match(db, tenants[0], tenants[1])
    ensure_match(db, tenants[2], tenants[3])
    ensure_match(db, tenants[4], tenants[5])
    ensure_reject(db, tenants[0], tenants[4])
    ensure_reject(db, tenants[6], tenants[2])


def create_package_data(db: Session, *, tenants: list[Account]) -> None:
    packages = [
        get_or_create_package(
            db,
            slug="starter",
            name="Starter",
            description="Gói cơ bản để dùng matching và chatbot trong 30 ngày.",
            price_cents=49000,
            credits_match=10,
            credits_chatbot=20,
            period="30_days",
            features=["matching", "chatbot"],
        ),
        get_or_create_package(
            db,
            slug="plus",
            name="Plus",
            description="Gói tăng lượt matching cho người đang tìm phòng tích cực.",
            price_cents=99000,
            credits_match=40,
            credits_chatbot=80,
            period="30_days",
            features=["matching", "chatbot", "priority_match"],
        ),
        get_or_create_package(
            db,
            slug="premium",
            name="Premium",
            description="Gói đầy đủ cho người cần tìm nhanh và ưu tiên hỗ trợ.",
            price_cents=199000,
            credits_match=120,
            credits_chatbot=240,
            period="30_days",
            features=["matching", "chatbot", "priority_match", "vip_listing"],
        ),
    ]

    purchases = [
        ensure_purchase(
            db,
            account=tenants[0],
            package=packages[0],
            provider_payment_id="sample-pay-tenant-demo-starter",
            status="paid",
        ),
        ensure_purchase(
            db,
            account=tenants[1],
            package=packages[1],
            provider_payment_id="sample-pay-tenant01-plus",
            status="paid",
        ),
        ensure_purchase(
            db,
            account=tenants[2],
            package=packages[2],
            provider_payment_id="sample-pay-tenant02-premium",
            status="pending",
        ),
    ]

    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    for account, purchase, package in zip(tenants[:3], purchases, packages, strict=True):
        ensure_entitlement(
            db,
            account=account,
            feature_key="match",
            quantity=package.credits_match,
            source_purchase=purchase,
            expires_at=expires_at,
        )
        ensure_entitlement(
            db,
            account=account,
            feature_key="chatbot",
            quantity=package.credits_chatbot,
            source_purchase=purchase,
            expires_at=expires_at,
        )
        ensure_entitlement(
            db,
            account=account,
            feature_key="active_subscription",
            quantity=None,
            source_purchase=purchase,
            expires_at=expires_at,
        )


def create_chatbot_data(db: Session, *, tenants: list[Account]) -> None:
    ensure_chat_session(
        db,
        account=tenants[0],
        title="Tìm phòng Quận Bình Thạnh",
        messages=[
            ("user", "Tìm giúp mình phòng ở Quận Bình Thạnh dưới 6 triệu."),
            (
                "assistant",
                "Mình tìm thấy phòng ban công khu D2 Bình Thạnh phù hợp ngân sách của bạn.",
            ),
        ],
    )
    ensure_chat_session(
        db,
        account=tenants[1],
        title="Tìm phòng Đồng Nai",
        messages=[
            ("user", "Có phòng nào ở Đồng Nai gần khu công nghiệp không?"),
            (
                "assistant",
                "Bạn có thể xem Studio gần khu công nghiệp Long Thành hoặc phòng rộng gần Nhơn Trạch.",
            ),
        ],
    )


def seed() -> None:
    db = SessionLocal()
    try:
        _, landlords, tenants, _ = create_accounts(db)
        amenities = create_amenities(db)
        rooms, posts = create_rooms_and_posts(
            db,
            landlords=landlords,
            amenities=amenities,
        )
        create_engagement_data(db, tenants=tenants, rooms=rooms, posts=posts)
        create_matching_data(db, tenants=tenants)
        create_package_data(db, tenants=tenants)
        create_chatbot_data(db, tenants=tenants)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
    print(
        "Sample data seeded: roles/accounts/profiles, 10 rooms, 10 posts, "
        "amenities, images, favorites, rental history, reviews, packages, "
        "purchases, entitlements, matching data, chatbot sessions/messages."
    )
