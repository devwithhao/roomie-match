from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import find_dotenv, load_dotenv
from sqlalchemy import engine_from_config, pool

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    """Load .env from typical locations (Windows-friendly: support cwd + repo root)."""
    candidates = [
        _REPO_ROOT / ".env",
        Path.cwd() / ".env",
    ]
    for path in candidates:
        if path.is_file():
            load_dotenv(path, override=False)

    found = find_dotenv(usecwd=True)
    if found:
        load_dotenv(found, override=False)


_load_dotenv()

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database.base import Base  # noqa: E402
from app.models.rooms import amenity as amenity_model  # noqa: F401, E402
from app.models.rooms import favorite as favorite_model  # noqa: F401, E402
from app.models.rooms import post as post_model  # noqa: F401, E402
from app.models.rooms import room as room_model  # noqa: F401, E402
from app.models.rooms import room_amenity as room_amenity_model  # noqa: F401, E402
from app.models.rooms import room_image as room_image_model  # noqa: F401, E402
from app.models.users import account as account_model  # noqa: F401, E402
from app.models.users import role as role_model  # noqa: F401, E402


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url and url.strip():
        return url.strip()
    hint_1 = f"Expected file: {_REPO_ROOT / '.env'}"
    hint_2 = f"Current directory .env exists: {(Path.cwd() / '.env').is_file()}"
    raise RuntimeError(
        "DATABASE_URL is required for migrations. "
        "Create a `.env` in the project root (next to `alembic.ini`) with "
        "`DATABASE_URL=mysql+pymysql://user:pass@host:3306/dbname?charset=utf8mb4`. "
        "Copy from `.env.example`. On Windows, ensure the file is named `.env` "
        "and not `.env.txt`. "
        f"{hint_1}. {hint_2}."
    )


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
