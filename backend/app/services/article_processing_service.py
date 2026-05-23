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

        categories_str = ", ".join(self.CATEGORIES[:-1])

        # Prepare image URLs for the prompt
        images_section = ""
        if image_urls:
            images_section = "\nAVAILABLE IMAGES TO EMBED IN ARTICLE:\n"
            for i, img_url in enumerate(image_urls, 1):
                images_section += f"{i}. {img_url}\n"
            images_section += "\nINSTRUCTIONS FOR IMAGES:\n- Analyze the article content and determine where images would be most relevant\n- Embed images naturally throughout the markdown using ![description](image_url) syntax\n- Place images contextually within paragraphs or between sections where they enhance the content\n- Use image descriptions that match the article content\n- Images can appear anywhere in the content, not just at the end\n"

        prompt = f"""You are a professional content editor and analyst. Process this article and generate ALL required metadata in a single JSON response.

ARTICLE CONTENT:
{content}
{images_section}

INSTRUCTIONS:
1. Generate a clear, engaging title (5-12 words) if not provided. Use the provided title if it exists.
2. Write a 2-3 sentence summary capturing main points and key findings
3. Classify into ONE category: {categories_str}, or Other
4. Generate 4-6 semantic tags (single words or short phrases, lowercase, hyphen-separated)
5. Structure article as CONCISE markdown with brief sections (~1000 chars max) - do NOT describe content in detail, only key points
6. Embed 2-3 most relevant images only (not every image URL)

PROVIDED TITLE: {title if title else "NOT PROVIDED - GENERATE ONE"}
PROVIDED AUTHOR: {author if author else "UNKNOWN"}

CATEGORIES (choose exactly one):
{categories_str}

CRITICAL INSTRUCTIONS FOR JSON RESPONSE:
- Return ONLY a valid JSON object (no markdown code blocks, no extra text before/after)
- Use proper JSON formatting with no unescaped quotes or newlines in string values
- IMPORTANT: Escape special characters in ALL string values:
  - Use \\n for actual line breaks
  - Use \\" for quotes
  - Use \\\\ for backslashes
- All markdown_content must have escaped newlines: use \\n instead of actual newlines
- Double-check JSON is valid before responding

JSON Response Format (MUST be exactly this structure):
{{
    "title": "Clear, engaging title under 100 chars",
    "summary": "2-3 sentence summary of main points",
    "category": "One of: AI, Web Development, DevOps, Security, Mobile, Cloud Computing, Data Science, Infrastructure, Blockchain, Other",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "markdown_content": "IMPORTANT: Use actual escaped newlines (\\\\n) for line breaks. Example: \\"## Section\\\\n\\\\nContent here\\\\n\\\\n## Next\\"."
}}

Important:
- Title: under 100 characters, engaging
- Summary: exactly 2-3 sentences
- Category: choose EXACTLY ONE from the list above
- Tags: 4-6 lowercase tags, hyphen-separated, no special chars
- Markdown: CONCISE formatting with brief headers and bullet points (max ~1000 chars) - NO detailed descriptions, only KEY POINTS
- Images: embed as ![description](url) contextually throughout content
- NO title or author in markdown_content, just body with embedded images
- MUST return ONLY the JSON object - nothing else!

JSON Response:"""

        # Retry logic for JSON parsing
        max_retries = 3
        for attempt in range(max_retries):
            try:
                attempt_start = time.time()
                logger.info(f"LLM API call (attempt {attempt + 1}/{max_retries})")
                response = await llm_client.generate(
                    prompt=prompt,
                    max_tokens=4096,
                    temperature=0.5,
                )
                attempt_elapsed = time.time() - attempt_start
                logger.info(f"LLM API call succeeded in {attempt_elapsed:.2f}s")

                logger.info(f"Raw response length: {len(response)} chars")
                logger.info(f"Full raw response:\n{response}")

                # Parse JSON response with improved extraction
                cleaned = response.strip()

                # First, try to remove markdown code blocks if present
                if cleaned.startswith('```'):
                    # Remove markdown code block markers
                    cleaned = re.sub(r'^```(json)?\s*', '', cleaned, flags=re.MULTILINE)
                    cleaned = re.sub(r'```\s*$', '', cleaned, flags=re.MULTILINE)
                    cleaned = cleaned.strip()
                    logger.debug("Removed markdown code block markers")

                try:
                    data = json.loads(cleaned)
                except json.JSONDecodeError as initial_error:
                    logger.debug(f"Initial JSON parse failed, attempting to fix unescaped newlines. Error: {str(initial_error)}")

                    # Fix unescaped newlines in JSON strings
                    # This happens when Bedrock returns actual newlines instead of \n escapes
                    # We need to escape them while preserving the JSON structure
                    try:
                        # Find the first { and last }
                        start_idx = cleaned.find('{')
                        end_idx = cleaned.rfind('}')

                        if start_idx >= 0 and end_idx > start_idx:
                            json_part = cleaned[start_idx:end_idx+1]

                            # Replace actual newlines with escaped newlines in the JSON
                            # But be careful not to break the JSON structure
                            # This is a careful approach: replace \n with \\n in string contexts
                            fixed_json = json_part.replace('\n', '\\n')

                            logger.debug("Fixed unescaped newlines in JSON")
                            data = json.loads(fixed_json)
                        else:
                            raise ValueError("Could not locate JSON bounds")
                    except Exception as fix_error:
                        logger.warning(f"Newline fix failed: {str(fix_error)}, trying brace extraction...")

                    # Try to extract and clean JSON from response
                    # Look for { and match closing }
                    start_idx = cleaned.find('{')
                    if start_idx == -1:
                        raise ValueError("Could not find JSON start in response")

                    # Find the matching closing brace
                    brace_count = 0
                    end_idx = -1
                    for i in range(start_idx, len(cleaned)):
                        if cleaned[i] == '{':
                            brace_count += 1
                        elif cleaned[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i
                                break

                    if end_idx == -1:
                        logger.error(f"Could not find matching closing brace. Response length: {len(cleaned)}")
                        logger.error(f"First 1000 chars of response: {cleaned[:1000]}")
                        raise ValueError("Could not find matching closing brace in response")

                    json_str = cleaned[start_idx:end_idx+1]
                    logger.debug(f"Extracted JSON ({len(json_str)} chars): {json_str[:300]}...")

                    # Try to parse the extracted JSON
                    try:
                        data = json.loads(json_str)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Initial JSON parse error: {str(initial_error)}")
                        logger.warning(f"Extracted JSON parse error: {str(e)}")
                        logger.warning(f"Extracted JSON (first 500 chars): {json_str[:500]}")
                        raise ValueError(f"Invalid JSON after extraction: {str(e)}")

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

                # Get markdown content (already includes images embedded contextually)
                markdown_base = data.get("markdown_content", "").strip()

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
                    logger.info("Falling back to basic article structure with raw content")
                    return {
                        "title": title or "Untitled",
                        "summary": content[:200] + "..." if content else None,
                        "category": "Other",
                        "tags": [],
                        "author": author,
                        "structured_markdown": f"# {title or 'Untitled'}\n\n{content}",
                    }
            except Exception as e:
                logger.error(f"Processing attempt {attempt + 1} failed: {str(e)}")
                if attempt == max_retries - 1:
                    logger.error(f"All processing attempts exhausted. Falling back to raw content.")
                    return {
                        "title": title or "Untitled",
                        "summary": content[:200] + "..." if content else None,
                        "category": "Other",
                        "tags": [],
                        "author": author,
                        "structured_markdown": f"# {title or 'Untitled'}\n\n{content}",
                    }

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
