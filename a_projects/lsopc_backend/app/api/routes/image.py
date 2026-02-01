# -*- coding: utf-8 -*-
from fastapi import APIRouter, HTTPException, Depends, Request
from app.schemas.image import ImageGenerateRequest, ImageGenerateResponse
from app.schemas.auth import UserBase
from app.api.routes.auth import get_current_user
from app.services.image_service import image_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/generate", response_model=ImageGenerateResponse)
async def generate_image(
    request_data: ImageGenerateRequest, 
    request: Request,
    current_user: UserBase = Depends(get_current_user)
):
    """
    Generate an image based on the provided prompt with authentication.
    """
    try:
        image_path = await image_service.generate_image(
            prompt=request_data.prompt,
            username=current_user.username,
            size=request_data.size,
            quality=request_data.quality
        )
        
        # Construct full URL
        if image_path:
            full_url = f"{str(request.base_url).rstrip('/')}{image_path}"
        else:
            full_url = None

        return ImageGenerateResponse(status="success", image_url=full_url)
    except Exception as e:
        logger.error(f"Failed to generate image: {e}")
        raise HTTPException(status_code=500, detail=str(e))
