"""Image storage service for uploading images to S3."""

import logging
import hashlib
import urllib.parse
from io import BytesIO
from typing import Optional
import asyncio
import requests
import boto3
from app.config import settings

logger = logging.getLogger(__name__)


class ImageStorageService:
    """Service for storing images in S3 and managing image URLs."""

    def __init__(self):
        """Initialize S3 client."""
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)
        self.bucket = settings.s3_bucket
        self.images_prefix = settings.s3_images_prefix

    async def download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL asynchronously.

        Args:
            url: Image URL to download

        Returns:
            Image bytes or None if download fails
        """
        if not url:
            return None

        try:
            loop = asyncio.get_event_loop()
            image_bytes = await loop.run_in_executor(
                None,
                self._download_image_sync,
                url
            )
            return image_bytes
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {str(e)}")
            return None

    def _download_image_sync(self, url: str) -> Optional[bytes]:
        """Synchronous image download helper.

        Args:
            url: Image URL to download

        Returns:
            Image bytes or None if download fails
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                return response.content
            else:
                logger.warning(f"Failed to download image from {url}: HTTP {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {str(e)}")
            return None

    def _generate_s3_key(self, url: str, original_filename: str = "") -> str:
        """Generate unique S3 key for image.

        Args:
            url: Original image URL
            original_filename: Original filename if available

        Returns:
            S3 key path
        """
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]

        if original_filename:
            filename = original_filename.replace(' ', '_')
        else:
            filename = f"image_{url_hash}"

        return f"{self.images_prefix}{filename}_{url_hash}"

    def upload_to_s3(self, image_bytes: bytes, url: str, filename: str = "") -> Optional[str]:
        """Upload image to S3.

        Args:
            image_bytes: Image file bytes
            url: Original image URL (for generating unique key)
            filename: Optional original filename

        Returns:
            S3 URL of uploaded image or None if upload fails
        """
        if not image_bytes:
            return None

        try:
            s3_key = self._generate_s3_key(url, filename)

            logger.debug(f"Uploading image to S3: {s3_key}")

            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=BytesIO(image_bytes),
                ContentType='image/jpeg',
            )

            s3_url = f"https://{self.bucket}.s3.{settings.aws_region}.amazonaws.com/{s3_key}"
            logger.info(f"Image uploaded successfully: {s3_url}")
            return s3_url
        except Exception as e:
            logger.error(f"Error uploading image to S3: {str(e)}")
            return None

    async def download_and_upload_image(self, image_url: str, filename: str = "") -> Optional[str]:
        """Download image from URL and upload to S3.

        Args:
            image_url: Image URL to download
            filename: Optional original filename

        Returns:
            S3 URL of uploaded image or None if process fails
        """
        if not image_url:
            return None

        logger.debug(f"Processing image: {image_url}")

        image_bytes = await self.download_image(image_url)
        if not image_bytes:
            return None

        s3_url = self.upload_to_s3(image_bytes, image_url, filename)
        return s3_url

    def format_markdown_image(self, image_url: str, alt_text: str = "Article image") -> str:
        """Format image as markdown.

        Args:
            image_url: Image URL (can be S3 URL)
            alt_text: Alt text for image

        Returns:
            Markdown formatted image
        """
        return f"![{alt_text}]({image_url})\n"
