# -*- coding: utf-8 -*-
from typing import Optional
from pydantic import BaseModel, Field

class ImageGenerateRequest(BaseModel):
    prompt: str = Field(..., description="The prompt to generate the image from.")
    size: Optional[str] = Field("1024x1024", description="The size of the generated image.")
    quality: Optional[str] = Field("high", description="The quality of the generated image (high/low/auto).")

class ImageGenerateResponse(BaseModel):
    status: str
    image_url: Optional[str] = None
    message: Optional[str] = None
