"""
Unit tests for OpenAI Vision Service
"""

import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from application.services.openai.vision_service import VisionService


@pytest.fixture
def sample_image_bytes():
    """Create sample image bytes."""
    # Minimal valid JPEG header
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"


@pytest.fixture
def temp_image_file(tmp_path, sample_image_bytes):
    """Create temporary image file."""
    image_file = tmp_path / "test.jpg"
    image_file.write_bytes(sample_image_bytes)
    return str(image_file)


class TestEncodeImageFromFile:
    """Test image encoding from file."""

    def test_encode_image_from_file_success(self, temp_image_file):
        """Test successful image encoding from file."""
        encoded = VisionService.encode_image_from_file(temp_image_file)
        assert isinstance(encoded, str)
        assert len(encoded) > 0

    def test_encode_image_from_file_not_found(self):
        """Test encoding non-existent file."""
        with pytest.raises(FileNotFoundError):
            VisionService.encode_image_from_file("/nonexistent/image.jpg")

    def test_encode_image_from_file_unsupported_format(self, tmp_path):
        """Test encoding unsupported file format."""
        unsupported_file = tmp_path / "test.bmp"
        unsupported_file.write_bytes(b"test")
        with pytest.raises(ValueError, match="Unsupported image format"):
            VisionService.encode_image_from_file(str(unsupported_file))

    def test_encode_image_from_file_formats(self, tmp_path):
        """Test encoding various supported formats."""
        for fmt in ["jpg", "jpeg", "png", "gif", "webp"]:
            image_file = tmp_path / f"test.{fmt}"
            image_file.write_bytes(b"test_data")
            encoded = VisionService.encode_image_from_file(str(image_file))
            assert isinstance(encoded, str)


class TestEncodeImageFromBytes:
    """Test image encoding from bytes."""

    def test_encode_image_from_bytes_success(self, sample_image_bytes):
        """Test successful image encoding from bytes."""
        encoded = VisionService.encode_image_from_bytes(sample_image_bytes)
        assert isinstance(encoded, str)
        assert len(encoded) > 0

    def test_encode_image_from_bytes_unsupported_format(self, sample_image_bytes):
        """Test encoding with unsupported format."""
        with pytest.raises(ValueError, match="Unsupported image format"):
            VisionService.encode_image_from_bytes(sample_image_bytes, "bmp")

    def test_encode_image_from_bytes_formats(self, sample_image_bytes):
        """Test encoding with various formats."""
        for fmt in ["jpeg", "png", "gif", "webp"]:
            encoded = VisionService.encode_image_from_bytes(sample_image_bytes, fmt)
            assert isinstance(encoded, str)

    def test_encode_image_from_bytes_decodable(self, sample_image_bytes):
        """Test encoded bytes can be decoded."""
        encoded = VisionService.encode_image_from_bytes(sample_image_bytes)
        decoded = base64.b64decode(encoded)
        assert decoded == sample_image_bytes


class TestDownloadImage:
    """Test image downloading."""

    @pytest.mark.asyncio
    async def test_download_image_success(self, sample_image_bytes):
        """Test successful image download."""
        with patch(
            "application.services.openai.vision_service.httpx.AsyncClient"
        ) as mock_client:
            mock_response = MagicMock()
            mock_response.content = sample_image_bytes
            mock_response.raise_for_status = MagicMock()

            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(return_value=mock_response)
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance

            result = await VisionService.download_image("http://example.com/image.jpg")
            assert result == sample_image_bytes

    @pytest.mark.asyncio
    async def test_download_image_failure(self):
        """Test image download failure."""
        with patch(
            "application.services.openai.vision_service.httpx.AsyncClient"
        ) as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get = AsyncMock(
                side_effect=Exception("Connection error")
            )
            mock_client_instance.__aenter__ = AsyncMock(
                return_value=mock_client_instance
            )
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_client_instance

            with pytest.raises(Exception):
                await VisionService.download_image("http://example.com/image.jpg")


class TestBuildVisionMessage:
    """Test vision message building."""

    def test_build_vision_message_with_url(self):
        """Test building vision message with URL."""
        message = VisionService.build_vision_message(
            "Describe this image", image_url="http://example.com/image.jpg"
        )
        assert message["role"] == "user"
        assert len(message["content"]) == 2
        assert message["content"][0]["type"] == "text"
        assert message["content"][1]["type"] == "image_url"

    def test_build_vision_message_with_file(self, temp_image_file):
        """Test building vision message with file."""
        message = VisionService.build_vision_message(
            "Describe this image", image_path=temp_image_file
        )
        assert message["role"] == "user"
        assert len(message["content"]) == 2
        assert message["content"][0]["type"] == "text"
        assert message["content"][1]["type"] == "image_url"

    def test_build_vision_message_with_bytes(self, sample_image_bytes):
        """Test building vision message with bytes."""
        message = VisionService.build_vision_message(
            "Describe this image", image_bytes=sample_image_bytes
        )
        assert message["role"] == "user"
        assert len(message["content"]) == 2
        assert message["content"][0]["type"] == "text"
        assert message["content"][1]["type"] == "image_url"

    def test_build_vision_message_no_image(self):
        """Test building vision message without image."""
        with pytest.raises(ValueError, match="At least one image source"):
            VisionService.build_vision_message("Describe this image")

    def test_build_vision_message_multiple_images(self, sample_image_bytes):
        """Test building vision message with multiple image sources."""
        with pytest.raises(ValueError, match="Only one image source"):
            VisionService.build_vision_message(
                "Describe this image",
                image_url="http://example.com/image.jpg",
                image_bytes=sample_image_bytes,
            )


class TestBuildMultiImageMessage:
    """Test multi-image message building."""

    def test_build_multi_image_message_urls(self):
        """Test building multi-image message with URLs."""
        urls = ["http://example.com/image1.jpg", "http://example.com/image2.jpg"]
        message = VisionService.build_multi_image_message("Compare these images", urls)
        assert message["role"] == "user"
        assert len(message["content"]) == 3  # 1 text + 2 images
        assert message["content"][0]["type"] == "text"
        assert message["content"][1]["type"] == "image_url"
        assert message["content"][2]["type"] == "image_url"

    def test_build_multi_image_message_bytes(self, sample_image_bytes):
        """Test building multi-image message with bytes."""
        images = [sample_image_bytes, sample_image_bytes]
        message = VisionService.build_multi_image_message(
            "Compare these images", images
        )
        assert message["role"] == "user"
        assert len(message["content"]) == 3  # 1 text + 2 images

    def test_build_multi_image_message_mixed(self, sample_image_bytes):
        """Test building multi-image message with mixed sources."""
        images = ["http://example.com/image1.jpg", sample_image_bytes]
        message = VisionService.build_multi_image_message(
            "Compare these images", images
        )
        assert message["role"] == "user"
        assert len(message["content"]) == 3

    def test_build_multi_image_message_empty(self):
        """Test building multi-image message with empty list."""
        with pytest.raises(ValueError, match="At least one image"):
            VisionService.build_multi_image_message("Compare these images", [])

    def test_build_multi_image_message_invalid_type(self):
        """Test building multi-image message with invalid type."""
        with pytest.raises(ValueError, match="Invalid image type"):
            VisionService.build_multi_image_message("Compare these images", [123])


class TestGetVisionModel:
    """Test vision model selection."""

    def test_get_vision_model_gpt4o(self):
        """Test getting GPT-4o vision model."""
        model = VisionService.get_vision_model("gpt-4o")
        assert model == "gpt-4o"

    def test_get_vision_model_gpt4o_mini(self):
        """Test getting GPT-4o mini vision model."""
        model = VisionService.get_vision_model("gpt-4o-mini")
        assert model == "gpt-4o-mini"

    def test_get_vision_model_default(self):
        """Test default vision model."""
        model = VisionService.get_vision_model()
        assert model == "gpt-4o"

    def test_get_vision_model_unsupported(self):
        """Test unsupported model defaults to gpt-4o."""
        model = VisionService.get_vision_model("unsupported-model")
        assert model == "gpt-4o"
