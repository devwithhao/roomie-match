from __future__ import annotations

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.features.users.dependencies import get_current_account
from app.features.users.models.account import Account
from app.features.users.models.role import Role
from app.features.users.role_utils import canonical_account_type


def require_landlord_account(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_db),
) -> Account:
    role = db.get(Role, account.role_id)
    if role is None or canonical_account_type(role.name, role.description) != "landlord":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Landlord permission required",
        )
    return account
