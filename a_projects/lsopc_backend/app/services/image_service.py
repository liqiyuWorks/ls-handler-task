# -*- coding: utf-8 -*-
import logging
import base64
import uuid
import os
import os
from datetime import datetime
from openai import OpenAI
from app.config import settings
from app.services.database import db

logger = logging.getLogger(__name__)

class ImageService:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.IMAGE_API_KEY,
            base_url=settings.IMAGE_BASE_URL
        )

    async def generate_image(self, prompt: str, username: str, size: str = "1024x1024", quality: str = "high"):
        """
        Generate an image using the configured AI service.
        """
        try:
            logger.info(f"Generating image with prompt: {prompt}")
            response = self.client.images.generate(
                model=settings.IMAGE_MODEL,
                prompt=prompt,
                n=1,
                size=size,
                quality=quality
            )
            logger.info(f"Image generation response received.")
            if not response.data:
                logger.error(f"No data returned in response: {response}")
                return None
            
            image_url = getattr(response.data[0], 'url', None)
            if not image_url and hasattr(response.data[0], 'b64_json'):
                b64_data = response.data[0].b64_json
                if b64_data:
                    # Save b64 to file
                    filename = f"image_{uuid.uuid4().hex}.png"
                    filepath = os.path.join("static", "images", filename)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(b64_data))
                    
                    # Return local URL (assuming standard host for now, or just relative)
                    # Ideally we'd get the base URL from the request, but for simplicity:
                    image_url = f"/static/images/{filename}"
                    logger.info(f"Image saved locally: {image_url}")
            
            # Save record to database
            if image_url:
                history_record = {
                    "username": username,
                    "prompt": prompt,
                    "image_url": image_url,
                    "size": size,
                    "quality": quality,
                    "created_at": datetime.utcnow()
                }
                await db.db.image_history.insert_one(history_record)
                logger.info(f"Image generation record saved to DB for user: {username}")

            logger.info(f"Image generation result: {image_url}")
            return image_url
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            raise e

image_service = ImageService()
