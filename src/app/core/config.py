from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    jwt_secret: str
    jwt_expire_minutes: int = 60
    groq_api_key: str = ""
    # Neu true: loi 500 tu register se kem thong bao loi DB (chi localhost/debug)
    app_debug: bool = Field(default=False, validation_alias="APP_DEBUG")
    google_client_id: str = ""
    
    # VNPAY Settings
    vnpay_tmn_code: str = ""
    vnpay_hash_secret: str = ""
    vnpay_url: str = "https://sandbox.vnpayment.vn/paymentv2/vpcpay.html"
    vnpay_return_url: str = "http://localhost:5173/payment/vnpay-return"
    
    # Cloudinary
    cloudinary_cloud_name: str = ""
    cloudinary_api_key: str = ""
    cloudinary_api_secret: str = ""


settings = Settings()
