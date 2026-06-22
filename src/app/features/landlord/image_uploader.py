from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import BinaryIO
from urllib.parse import urlparse

from fastapi import HTTPException, status

from app.core.config import settings


def upload_room_image(file: BinaryIO, filename: str | None = None) -> str:
    return upload_public_image(file, filename=filename, folder="rooms")


def upload_verification_image(file: BinaryIO, filename: str | None = None) -> str:
    return upload_public_image(file, filename=filename, folder="verifications")


def upload_public_image(file: BinaryIO, *, filename: str | None = None, folder: str) -> str:
    provider = settings.image_storage_provider.strip().lower()
    if provider == "local":
        return _upload_local(file, filename=filename, folder=folder)
    if provider == "cloudinary":
        return _upload_cloudinary(file, filename=filename, folder=folder)
    if provider == "cloudflare":
        return _upload_cloudflare(file, filename=filename, folder=folder)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Unsupported image storage provider: {settings.image_storage_provider}",
    )


def local_public_path(image_url: str) -> Path | None:
    parsed = urlparse(image_url)
    if parsed.scheme or parsed.netloc:
        return None

    public_root = settings.public_storage_url.rstrip("/")
    normalized_path = parsed.path.rstrip("/")
    if not normalized_path.startswith(public_root):
        return None

    relative = normalized_path[len(public_root):].lstrip("/")
    target = (Path(settings.local_storage_dir) / relative).resolve()
    base = Path(settings.local_storage_dir).resolve()
    if target != base and base not in target.parents:
        raise HTTPException(status_code=404, detail="Image not found")
    return target


def _upload_cloudinary(file: BinaryIO, *, filename: str | None, folder: str) -> str:
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
        folder=f"{settings.cloudinary_folder.rstrip('/')}/{folder}",
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


def _upload_cloudflare(file: BinaryIO, *, filename: str | None, folder: str) -> str:
    if not (settings.cloudflare_account_id and settings.cloudflare_api_token):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloudflare Images is not configured",
        )

    try:
        import httpx
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="httpx dependency is required for Cloudflare uploads",
        ) from exc

    suffix = Path(filename or "").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = ".jpg"
    generated_name = f"{uuid.uuid4().hex}{suffix}"
    upload_name = filename or generated_name
    custom_id = f"{folder}/{generated_name}"

    try:
        file.seek(0)
    except (AttributeError, OSError):
        pass

    response = httpx.post(
        f"https://api.cloudflare.com/client/v4/accounts/{settings.cloudflare_account_id}/images/v1",
        headers={"Authorization": f"Bearer {settings.cloudflare_api_token}"},
        files={"file": (upload_name, file)},
        data={
            "id": custom_id,
            "metadata": json.dumps({"folder": folder}),
            "requireSignedURLs": "false",
        },
        timeout=60,
    )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Cloudflare upload failed: {response.text}",
        )

    body = response.json()
    result = body.get("result") or {}
    variants = result.get("variants") or []
    if variants:
        return str(variants[0])

    if settings.cloudflare_delivery_url:
        return f"{settings.cloudflare_delivery_url.rstrip('/')}/{result.get('id')}/public"

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Cloudflare did not return a delivery URL",
    )


def _upload_local(file: BinaryIO, *, filename: str | None = None, folder: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        suffix = ".jpg"

    storage_root = Path(settings.local_storage_dir)
    target_dir = storage_root / folder
    target_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}{suffix}"
    target = target_dir / stored_name

    try:
        file.seek(0)
    except (AttributeError, OSError):
        pass

    with target.open("wb") as out_file:
        shutil.copyfileobj(file, out_file)

    public_root = settings.public_storage_url.rstrip("/")
    return f"{public_root}/{folder}/{stored_name}"
