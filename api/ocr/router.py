import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from api.ocr.models import OCRResponse
from middlewares.auth import auth_middleware
from services.uni import ocr_service

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}

router = APIRouter(prefix="/ocr")


async def process_image_file(file: UploadFile) -> bytes:
    if not file.content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed"
        )
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed"
        )
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File name not allowed"
        )

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File type not allowed"
        )

    file_data = await file.read()
    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File is empty"
        )

    return file_data


@router.post("/normal", response_model=OCRResponse)
async def normal_ocr(file: UploadFile = File(...), _: None = Depends(auth_middleware)):
    try:
        file_data = await process_image_file(file)
        result = ocr_service.normal_ocr(file_data)
        return OCRResponse(
            content=result.content,
            confidence=result.confidence,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/turbo", response_model=OCRResponse)
async def turbo_ocr(file: UploadFile = File(...), _: None = Depends(auth_middleware)):
    try:
        file_data = await process_image_file(file)
        result = ocr_service.turbo_ocr(file_data)
        return OCRResponse(
            content=result.content,
            confidence=result.confidence,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
