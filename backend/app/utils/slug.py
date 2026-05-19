"""Slug generation utilities."""

from slugify import slugify


def generate_slug(text: str, max_length: int = 200) -> str:
    """Generate a URL-safe slug from text."""
    slug = slugify(text, max_length=max_length)
    return slug
