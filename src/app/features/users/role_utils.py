from __future__ import annotations

import unicodedata

from sqlalchemy import func, or_

from app.features.users.models.role import Role


ACCOUNT_TYPE_LABELS = {
    "admin": "Quản trị viên",
    "landlord": "Chủ trọ",
    "tenant": "Khách thuê",
}

ACCOUNT_TYPE_ALIASES = {
    "admin": ("admin", "administrator", "quan tri", "quản trị"),
    "landlord": ("landlord", "owner", "chu tro", "chủ trọ", "chu nha", "chủ nhà"),
    "tenant": ("tenant", "renter", "nguoi thue", "người thuê", "khach thue", "khách thuê"),
}


def normalize_role_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFD", value.strip().lower())
    without_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return " ".join(without_marks.replace("_", " ").replace("-", " ").split())


def canonical_account_type(name: str | None, description: str | None = None) -> str:
    text = normalize_role_text(f"{name or ''} {description or ''}")
    for account_type, aliases in ACCOUNT_TYPE_ALIASES.items():
        if any(normalize_role_text(alias) in text for alias in aliases):
            return account_type
    return normalize_role_text(name) or "tenant"


def account_type_label(account_type: str, fallback: str | None = None) -> str:
    return ACCOUNT_TYPE_LABELS.get(account_type, fallback or account_type)


def account_type_filter(account_type: str):
    aliases = ACCOUNT_TYPE_ALIASES.get(account_type, (account_type,))
    predicates = []
    for alias in aliases:
        normalized_alias = normalize_role_text(alias)
        raw_alias = alias.strip().lower()
        for candidate in {normalized_alias, raw_alias}:
            predicates.append(func.lower(Role.name).like(f"%{candidate}%"))
            predicates.append(func.lower(Role.description).like(f"%{candidate}%"))
    return or_(*predicates)
