from __future__ import annotations

import cloudinary
import cloudinary.uploader
from fastapi import APIRouter, File, HTTPException, UploadFile, status

router = APIRouter()


@router.post("/image")
def upload_image(file: UploadFile = File(...)) -> dict[str, str]:
    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an image",
            )

        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file.file,
            folder="roomie_match",
        )
        
        url = result.get("secure_url")
        if not url:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload image to Cloudinary",
            )
            
        return {"url": url}
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Upload Error:", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during upload: {str(e)}",
        )
