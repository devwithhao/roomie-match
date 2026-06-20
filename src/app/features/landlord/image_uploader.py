from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import BinaryIO

from fastapi import HTTPException, status

from app.core.config import settings


def upload_room_image(file: BinaryIO, filename: str | None = None) -> str:
    provider = settings.image_storage_provider.strip().lower()
    if provider == "local":
        return _upload_local(file, filename)
    if provider != "cloudinary":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unsupported image storage provider: {settings.image_storage_provider}",
        )

    if not (
        settings.cloudinary_cloud_name
        and settings.cloudinary_api_key
        and settings.cloudinary_api_secret
    ):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary is not configured",
        )

    try:
        import cloudinary
        import cloudinary.uploader
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudinary dependency is not installed",
        ) from exc

    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_api_secret,
        secure=True,
    )
    result = cloudinary.uploader.upload(
        file,
        folder=settings.cloudinary_folder,
        resource_type="image",
        public_id=None if not filename else filename.rsplit(".", 1)[0],
        overwrite=False,
    )
    url = result.get("secure_url")
    if not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Cloudinary did not return an image URL",
        )
    return str(url)


def _upload_local(file: BinaryIO, filename: str | None = None) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = ".jpg"

    storage_root = Path(settings.local_storage_dir)
    room_dir = storage_root / "rooms"
    room_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}{suffix}"
    target = room_dir / stored_name

    try:
        file.seek(0)
    except (AttributeError, OSError):
        pass

    with target.open("wb") as out_file:
        shutil.copyfileobj(file, out_file)

    public_root = settings.public_storage_url.rstrip("/")
    return f"{public_root}/rooms/{stored_name}"
