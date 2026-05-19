"""Enhanced article processing with consolidated single-call AI processing.

This module handles AI-powered content processing using a single Bedrock call
that generates all metadata (title, summary, category, tags, markdown) at once.
"""

import json
import logging
import re
from typing import Optional
import html
import time

logger = logging.getLogger(__name__)


class ArticleProcessingService:
    """Service for intelligent article processing using Bedrock Claude Haiku 4.5.

    Consolidated pipeline - single Bedrock call generates:
    1. Title
    2. Summary (2-3 sentences)
    3. Category
    4. Tags (4-6 semantic tags)
    5. Structured markdown (with embedded images)
    """

    CATEGORIES = [
        "AI",
        "Web Development",
        "DevOps",
        "Security",
        "Mobile",
        "Cloud Computing",
        "Data Science",
        "Infrastructure",
        "Blockchain",
        "Other"
    ]

    async def process_article_content(
        self,
        title: str,
        content: str,
        author: Optional[str] = None,
    ) -> dict:
        """Process article content to extract all metadata in one call."""
        if not content or len(content.strip()) < 100:
            return {
                "summary": None,
                "passages": [],
                "category": "Other",
                "tags": [],
                "structured_markdown": None,
            }

        max_length = 5000
        content_for_processing = content[:max_length] + ("..." if len(content) > max_length else "")

        try:
            from app.integrations.llm_client import get_llm_client
            llm_client = await get_llm_client()

            # Single consolidated call
            result = await self._process_all_fields(
                llm_client, title, content_for_processing, author, []
            )

            return result

        except Exception as e:
            logger.error(f"Error processing article: {str(e)}")
            return {
                "summary": None,
                "passages": [],
                "category": "Other",
                "tags": [],
                "structured_markdown": None,
            }

    async def process_url_content(
        self,
        url: str,
        raw_content: str,
        title: Optional[str] = None,
        author: Optional[str] = None,
        image_urls: Optional[list[str]] = None,
    ) -> dict:
        """Process content from URL and generate all metadata in a single Bedrock call.

        Args:
            url: Source URL
            raw_content: Raw HTML from scraping
            title: Custom title (auto-generated if None)
            author: Author name
            image_urls: List of S3 image URLs from scraping

        Returns:
            dict with title, summary, category, tags, author, structured_markdown
        """
        logger.info(f"Processing URL content for: {url}")
        start_time = time.time()

        if not raw_content or len(raw_content.strip()) < 100:
            logger.warning(f"Insufficient content for URL {url} (< 100 chars)")
            return {
                "title": title or "Untitled",
                "summary": None,
                "category": "Other",
                "tags": [],
                "author": author,
                "structured_markdown": None,
            }

        # Extract clean text from HTML
        logger.debug(f"Extracting clean text from HTML/markdown (size: {len(raw_content)} chars)")
        content_text = self._extract_text_from_html(raw_content)

        if not content_text or len(content_text.strip()) < 100:
            logger.warning(f"Insufficient clean content extracted for {url}")
            return {
                "title": title or "Untitled",
                "summary": None,
                "category": "Other",
                "tags": [],
                "author": author,
                "structured_markdown": None,
            }

        logger.debug(f"Extracted clean text: {len(content_text)} chars")

        # Truncate for API limits
        max_length = 5000
        content_for_processing = content_text[:max_length] + ("..." if len(content_text) > max_length else "")
        logger.debug(f"Content prepared for LLM: {len(content_for_processing)} chars, images: {len(image_urls or [])}")

        try:
            from app.integrations.llm_client import get_llm_client
            llm_client = await get_llm_client()

            # Single consolidated call generates everything
            result = await self._process_all_fields(
                llm_client,
                title,
                content_for_processing,
                author,
                image_urls or [],
                content_text  # Full content for markdown structuring
            )

            elapsed = time.time() - start_time
            logger.info(f"[SUCCESS] URL content processing complete in {elapsed:.2f}s: "
                       f"title='{result['title']}', category={result['category']}, tags={len(result['tags'])}")

            return result

        except Exception as e:
            logger.error(f"[ERROR] Error processing URL content for {url}: {type(e).__name__}: {str(e)}")
            logger.debug("Error details:", exc_info=True)
            return {
                "title": title or "Untitled",
                "summary": None,
                "category": "Other",
                "tags": [],
                "author": author,
                "structured_markdown": None,
            }

    async def _process_all_fields(
        self,
        llm_client,
        title: Optional[str],
        content: str,
        author: Optional[str],
        image_urls: list[str],
        full_content: Optional[str] = None,
    ) -> dict:
        """Single consolidated Bedrock call to generate all fields at once."""

        # Prepare image references for markdown
        image_markdown = ""
        if image_urls:
            image_markdown = "\n\n## 📸 Article Images\n"
            for i, img_url in enumerate(image_urls, 1):
                image_markdown += f"\n![Article Image {i}]({img_url})\n"

        categories_str = ", ".join(self.CATEGORIES[:-1])

        prompt = f"""You are a professional content editor and analyst. Process this article and generate ALL required metadata in a single JSON response.

ARTICLE CONTENT:
{content}

INSTRUCTIONS:
1. Generate a clear, engaging title (5-12 words) if not provided. Use the provided title if it exists.
2. Write a 2-3 sentence summary capturing main points and key findings
3. Classify into ONE category: {categories_str}, or Other
4. Generate 4-6 semantic tags (single words or short phrases, lowercase, hyphen-separated)
5. Structure full article as markdown with proper headers and formatting

PROVIDED TITLE: {title if title else "NOT PROVIDED - GENERATE ONE"}
PROVIDED AUTHOR: {author if author else "UNKNOWN"}

CATEGORIES (choose exactly one):
{categories_str}

Return ONLY valid JSON (no markdown, no backticks) with this exact structure:
{{
    "title": "Generated or provided title",
    "summary": "2-3 sentence summary",
    "category": "One of the listed categories",
    "tags": ["tag1", "tag2", "tag3", "tag4"],
    "markdown_content": "Full article markdown content with headers, paragraphs, lists as appropriate"
}}

Remember:
- Title must be under 100 characters
- Summary must be 2-3 sentences
- Tags must be lowercase and hyphen-separated
- Markdown must use proper formatting (headers with #, bold with **, lists with -, etc.)
- Do NOT include title or author in the markdown_content - just the article body
- Return ONLY the JSON object, nothing else

JSON Response:"""

        # Retry logic for JSON parsing
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Bedrock API call (attempt {attempt + 1}/{max_retries})")
                response = await llm_client.generate(
                    prompt=prompt,
                    max_tokens=3000,
                    temperature=0.5,
                )

                logger.debug(f"Raw response length: {len(response)} chars")

                # Parse JSON response
                try:
                    data = json.loads(response.strip())
                except json.JSONDecodeError:
                    # Try to extract JSON from response if it has extra text
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                    if json_match:
                        data = json.loads(json_match.group())
                    else:
                        raise ValueError("Could not find JSON in response")

                # Extract and validate fields
                generated_title = (data.get("title") or title or "Untitled").strip()
                if not generated_title or generated_title == "NOT PROVIDED - GENERATE ONE":
                    generated_title = "Untitled"

                summary = data.get("summary", "").strip() or None
                category = data.get("category", "Other").strip()
                tags_raw = data.get("tags", [])

                # Validate category
                if category not in self.CATEGORIES:
                    for cat in self.CATEGORIES:
                        if cat.lower() in category.lower() or category.lower() in cat.lower():
                            category = cat
                            break
                    else:
                        category = "Other"

                # Validate and clean tags
                clean_tags = []
                if isinstance(tags_raw, list):
                    for tag in tags_raw:
                        if isinstance(tag, str) and tag.strip():
                            clean_tag = tag.strip().lower().replace(" ", "-")[:50]
                            clean_tags.append(clean_tag)
                clean_tags = clean_tags[:10]

                # Get markdown content
                markdown_base = data.get("markdown_content", "").strip()

                # Add images to markdown
                if image_urls:
                    markdown_base += image_markdown

                # Build final markdown with metadata
                final_markdown = self._build_final_markdown(
                    generated_title, author, summary, markdown_base
                )

                logger.debug(f"Successfully parsed all fields - title: {len(generated_title)}, "
                           f"summary: {bool(summary)}, category: {category}, tags: {len(clean_tags)}")

                return {
                    "title": generated_title,
                    "summary": summary,
                    "category": category,
                    "tags": clean_tags,
                    "author": author,
                    "structured_markdown": final_markdown,
                }

            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"All JSON parse attempts failed after {max_retries} tries")
                    return {
                        "title": title or "Untitled",
                        "summary": None,
                        "category": "Other",
                        "tags": [],
                        "author": author,
                        "structured_markdown": None,
                    }
            except Exception as e:
                logger.error(f"Processing attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    raise

    def _build_final_markdown(
        self,
        title: str,
        author: Optional[str],
        summary: Optional[str],
        content: str,
    ) -> str:
        """Build final markdown with title, author, summary, and content."""
        md_parts = [f"# {title}\n"]

        if author:
            md_parts.append(f"**By {author}**\n")

        md_parts.append("---\n")

        if summary:
            md_parts.append("## 📋 Summary\n")
            md_parts.append(f"> {summary}\n")
            md_parts.append("")

        md_parts.append(content)

        return "\n".join(md_parts)

    def _extract_text_from_html(self, html_content: str) -> str:
        """Extract clean text from HTML content."""
        # Unescape HTML entities
        text = html.unescape(html_content)

        # Remove script and style
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)

        # Clean whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n\n'.join(lines)
        text = ' '.join(text.split())

        return text.strip()
