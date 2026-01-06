"""
Vision/Multimodal Service for OpenAI SDK

Provides utilities for handling images and multimodal content with OpenAI.
"""

import base64
import logging
import os
from typing import Dict, List, Optional, Union

import httpx

logger = logging.getLogger(__name__)


class VisionService:
    """Handle vision and multimodal capabilities with OpenAI."""

    # Supported image formats
    SUPPORTED_FORMATS = {"jpeg", "jpg", "png", "gif", "webp"}

    # Vision models
    VISION_MODELS = {
        "gpt-4-vision": "gpt-4-vision-preview",
        "gpt-4o": "gpt-4o",
        "gpt-4o-mini": "gpt-4o-mini",
    }

    @staticmethod
    def encode_image_from_file(image_path: str) -> str:
        """
        Encode image file to base64.

        Args:
            image_path: Path to image file

        Returns:
            Base64 encoded image string

        Raises:
            FileNotFoundError: If image file not found
            ValueError: If file format not supported
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")

        file_ext = os.path.splitext(image_path)[1].lstrip(".").lower()
        if file_ext not in VisionService.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported image format: {file_ext}")

        try:
            logger.debug(f"Encoding image from file: {image_path}")
            with open(image_path, "rb") as image_file:
                encoded = base64.b64encode(image_file.read()).decode("utf-8")
            logger.debug(f"Image encoded successfully: {len(encoded)} bytes")
            return encoded
        except Exception as e:
            logger.error(f"Failed to encode image: {e}")
            raise

    @staticmethod
    def encode_image_from_bytes(image_bytes: bytes, format: str = "jpeg") -> str:
        """
        Encode image bytes to base64.

        Args:
            image_bytes: Raw image bytes
            format: Image format (jpeg, png, gif, webp)

        Returns:
            Base64 encoded image string

        Raises:
            ValueError: If format not supported
        """
        if format.lower() not in VisionService.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported image format: {format}")

        try:
            logger.debug(f"Encoding image from bytes: {len(image_bytes)} bytes")
            encoded = base64.b64encode(image_bytes).decode("utf-8")
            logger.debug(f"Image encoded successfully")
            return encoded
        except Exception as e:
            logger.error(f"Failed to encode image bytes: {e}")
            raise

    @staticmethod
    async def download_image(url: str) -> bytes:
        """
        Download image from URL.

        Args:
            url: Image URL

        Returns:
            Image bytes

        Raises:
            Exception: If download fails
        """
        try:
            logger.debug(f"Downloading image from URL: {url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=30.0)
                response.raise_for_status()
            logger.debug(f"Image downloaded: {len(response.content)} bytes")
            return response.content
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
            raise

    @staticmethod
    def _validate_image_sources(
        image_url: Optional[str],
        image_path: Optional[str],
        image_bytes: Optional[bytes],
    ) -> None:
        """Validate that exactly one image source is provided.

        Args:
            image_url: Image URL
            image_path: Image path
            image_bytes: Image bytes

        Raises:
            ValueError: If no image or multiple images provided
        """
        image_count = sum([
            image_url is not None,
            image_path is not None,
            image_bytes is not None
        ])

        if image_count == 0:
            raise ValueError("At least one image source must be provided")
        if image_count > 1:
            raise ValueError("Only one image source can be provided")

    @staticmethod
    def _build_image_content(
        image_url: Optional[str],
        image_path: Optional[str],
        image_bytes: Optional[bytes],
        image_format: str,
    ) -> Dict[str, any]:
        """Build image content block.

        Args:
            image_url: Image URL
            image_path: Image path
            image_bytes: Image bytes
            image_format: Image format

        Returns:
            Image content block dictionary
        """
        if image_url:
            logger.debug(f"Building vision message with URL: {image_url}")
            return {
                "type": "image_url",
                "image_url": {"url": image_url}
            }

        if image_path:
            logger.debug(f"Building vision message with file: {image_path}")
            base64_image = VisionService.encode_image_from_file(image_path)
            return {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{image_format};base64,{base64_image}"
                }
            }

        base64_image = VisionService.encode_image_from_bytes(image_bytes, image_format)
        logger.debug(f"Building vision message with bytes: {len(image_bytes)} bytes")
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:image/{image_format};base64,{base64_image}"
            }
        }

    @staticmethod
    def build_vision_message(
        text: str,
        image_url: Optional[str] = None,
        image_path: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        image_format: str = "jpeg",
    ) -> Dict[str, any]:
        """Build message with vision content.

        Args:
            text: Text content
            image_url: URL to image (optional)
            image_path: Path to local image (optional)
            image_bytes: Raw image bytes (optional)
            image_format: Image format if using image_bytes

        Returns:
            Message dictionary with vision content

        Raises:
            ValueError: If no image provided or multiple images provided
        """
        try:
            VisionService._validate_image_sources(image_url, image_path, image_bytes)

            content = [{"type": "text", "text": text}]
            image_content = VisionService._build_image_content(
                image_url, image_path, image_bytes, image_format
            )
            content.append(image_content)

            return {"role": "user", "content": content}

        except Exception as e:
            logger.error(f"Failed to build vision message: {e}")
            raise

    @staticmethod
    def build_multi_image_message(
        text: str,
        images: List[Union[str, bytes]],
        image_format: str = "jpeg",
    ) -> Dict[str, any]:
        """
        Build message with multiple images.

        Args:
            text: Text content
            images: List of image URLs or bytes
            image_format: Image format if using bytes

        Returns:
            Message dictionary with multiple images

        Raises:
            ValueError: If images list is empty
        """
        if not images:
            raise ValueError("At least one image must be provided")

        content = [{"type": "text", "text": text}]

        try:
            logger.debug(f"Building multi-image message with {len(images)} images")

            for i, image in enumerate(images):
                if isinstance(image, str):
                    # Assume it's a URL
                    content.append({
                        "type": "image_url",
                        "image_url": {"url": image}
                    })
                elif isinstance(image, bytes):
                    # Encode bytes to base64
                    base64_image = VisionService.encode_image_from_bytes(
                        image, image_format
                    )
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/{image_format};base64,{base64_image}"
                        }
                    })
                else:
                    raise ValueError(f"Invalid image type at index {i}: {type(image)}")

            return {"role": "user", "content": content}

        except Exception as e:
            logger.error(f"Failed to build multi-image message: {e}")
            raise

    @staticmethod
    def get_vision_model(model: str = "gpt-4o") -> str:
        """
        Get appropriate vision model name.

        Args:
            model: Model identifier

        Returns:
            Full model name for vision tasks

        Raises:
            ValueError: If model not supported for vision
        """
        if model in VisionService.VISION_MODELS:
            return VisionService.VISION_MODELS[model]
        elif model in VisionService.VISION_MODELS.values():
            return model
        else:
            logger.warning(f"Model {model} may not support vision, using gpt-4o")
            return "gpt-4o"

