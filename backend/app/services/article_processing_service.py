"""Enhanced article processing with intelligent summarization and structuring.

This module handles AI-powered content processing including:
- Title generation from content
- Intelligent summarization (2-3 sentences)
- Category detection (AI, Web Dev, DevOps, etc.)
- Semantic tag generation
- Structured markdown formatting
- Passage extraction and highlighting

Uses Claude via Bedrock (primary) with OpenAI fallback for all LLM operations.
"""

import json
import logging
import re
from typing import Optional
import html
import time

from app.integrations.llm_client import get_llm_client

logger = logging.getLogger(__name__)


class ArticleProcessingService:
    """Service for intelligent article processing using Claude/Bedrock.

    Handles all AI-powered content processing after web scraping:
    1. Title generation - Creates engaging titles from raw content
    2. Summary generation - 2-3 sentence executive summary
    3. Category detection - Classifies into tech categories
    4. Tag generation - Semantic tags for discovery
    5. Markdown structuring - Formats content with headers, lists, etc.
    6. Passage extraction - Identifies key quotes and insights

    All LLM calls use Bedrock (us-west-2) with OpenAI fallback.
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
        """
        Intelligently process article content to extract summary, passages, category, and tags.

        Returns:
            dict with keys: summary, passages, category, tags, structured_markdown
        """
        if not content or len(content.strip()) < 100:
            return {
                "summary": None,
                "passages": [],
                "category": "Other",
                "tags": [],
                "structured_markdown": None,
            }

        # Truncate content for API calls (avoid token limits)
        max_length = 5000
        content_for_processing = content[:max_length] + ("..." if len(content) > max_length else "")

        try:
            llm_client = await get_llm_client()

            # 1. Generate intelligent summary and extract passages in parallel
            summary, passages = await self._generate_summary_and_passages(
                llm_client, title, content_for_processing
            )

            # 2. Detect category
            category = await self._detect_category(
                llm_client, title, content_for_processing
            )

            # 3. Generate semantic tags
            tags = await self._generate_tags(
                llm_client, title, summary or content_for_processing[:500], category
            )

            # 4. Generate structured markdown
            structured_markdown = await self._generate_structured_markdown(
                title, author, summary, passages, content
            )

            return {
                "summary": summary,
                "passages": passages,
                "category": category,
                "tags": tags,
                "structured_markdown": structured_markdown,
            }

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
    ) -> dict:
        """Process content from URL via Crawl4AI and generate metadata.

        Pipeline:
        1. Validate content length (minimum 100 chars)
        2. Extract clean text from HTML/markdown
        3. Generate title (if not provided)
        4. Generate 2-3 sentence summary
        5. Detect category from content
        6. Generate semantic tags
        7. Format as structured markdown

        Args:
            url (str): Source URL
            raw_content (str): Raw HTML from Crawl4AI scraping
            title (Optional[str]): Custom title (auto-generated if None)
            author (Optional[str]): Author name

        Returns:
            dict: Processing result with keys:
                - title: Generated or provided title
                - summary: 2-3 sentence summary
                - category: Detected tech category
                - tags: Semantic tags list
                - author: Author name
                - structured_markdown: Formatted content

        Note:
            All LLM calls use Bedrock (us-west-2) with OpenAI fallback.
            Content is truncated to 5000 chars to avoid token limits.
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

        # Clean HTML entities and extract text
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

        # Truncate content for API calls (avoid token limits)
        max_length = 5000
        content_for_processing = content_text[:max_length] + ("..." if len(content_text) > max_length else "")
        logger.debug(f"Content prepared for LLM processing: {len(content_for_processing)} chars")

        try:
            logger.debug("Initializing LLM client")
            llm_client = await get_llm_client()

            # 1. Generate title from content if not provided
            generated_title = title
            if not generated_title:
                logger.info("Generating title from content via LLM")
                generated_title = await self._generate_title_from_content(
                    llm_client, content_for_processing
                )
                logger.debug(f"Generated title: {generated_title}")
            else:
                logger.debug(f"Using provided title: {generated_title}")

            # 2. Generate intelligent summary and extract passages
            logger.info("Generating summary and extracting passages via LLM")
            summary, passages = await self._generate_summary_and_passages(
                llm_client, generated_title, content_for_processing
            )
            logger.debug(f"Summary generated ({len(summary or '') } chars), {len(passages)} passages extracted")

            # 3. Detect category
            logger.info("Detecting content category via LLM")
            category = await self._detect_category(
                llm_client, generated_title, content_for_processing
            )
            logger.debug(f"Category detected: {category}")

            # 4. Generate semantic tags
            logger.info("Generating semantic tags via LLM")
            tags = await self._generate_tags(
                llm_client, generated_title, summary or content_for_processing[:500], category
            )
            logger.debug(f"Tags generated: {tags}")

            # 5. Generate structured markdown
            logger.info("Structuring content as markdown")
            structured_markdown = await self._generate_structured_markdown(
                generated_title, author, summary, passages, content_text
            )
            logger.debug(f"Structured markdown generated: {len(structured_markdown or '')} chars")

            elapsed = time.time() - start_time
            logger.info(f"[SUCCESS] URL content processing complete in {elapsed:.2f}s: title='{generated_title}', category={category}, tags={len(tags)}")

            return {
                "title": generated_title,
                "summary": summary,
                "category": category,
                "tags": tags,
                "author": author,
                "structured_markdown": structured_markdown,
            }

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

    def _extract_text_from_html(self, html_content: str) -> str:
        """
        Extract clean text from HTML content.

        Removes HTML tags and entities, preserving readability.
        """
        # First unescape HTML entities
        text = html.unescape(html_content)

        # Remove HTML tags using simple regex
        # This handles common cases but isn't a full HTML parser
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', ' ', text)

        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n\n'.join(lines)

        # Remove extra spaces
        text = ' '.join(text.split())

        return text.strip()

    async def _generate_title_from_content(
        self,
        llm_client,
        content: str,
    ) -> str:
        """Generate a natural title from content using LLM."""
        prompt = f"""You are a professional content editor. Read the following content and generate a clear, engaging title that captures the main topic or message.

The title should be:
- Concise (5-12 words)
- Engaging and descriptive
- Free of clickbait language
- Natural and professional

Content:
{content}

Return ONLY the title, nothing else."""

        try:
            response = await llm_client.generate(
                prompt=prompt,
                max_tokens=100,
                temperature=0.5,
            )

            title = response.strip().strip('"\'')

            # Ensure title is not empty and reasonable length
            if title and len(title) < 200:
                return title

            return "Untitled"

        except Exception as e:
            logger.warning(f"Error generating title from content: {str(e)}")
            return "Untitled"

    async def _generate_summary_and_passages(
        self,
        llm_client,
        title: str,
        content: str,
    ) -> tuple[Optional[str], list[dict]]:
        """Generate a 2-3 sentence summary and extract key passages."""
        prompt = f"""Analyze the following article and provide:
1. A concise 2-3 sentence summary capturing the main points and key findings
2. 2-4 key passages from the content, each with a brief description of why it's important

Return ONLY valid JSON with this exact structure (no markdown, no backticks):
{{"summary": "2-3 sentence summary here", "passages": [{{"text": "passage text here", "description": "why this matters"}}]}}

Article Title: {title}

Content:
{content}

JSON Response:"""

        try:
            response = await llm_client.generate(
                prompt=prompt,
                max_tokens=800,
                temperature=0.5,
            )

            # Parse JSON response
            data = json.loads(response.strip())
            summary = data.get("summary", "").strip()
            passages = data.get("passages", [])

            # Validate passages structure
            clean_passages = []
            for p in passages:
                if isinstance(p, dict) and "text" in p and "description" in p:
                    clean_passages.append({
                        "text": p["text"][:500],
                        "description": p["description"][:250]
                    })

            return summary if summary else None, clean_passages

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse summary/passages JSON: {str(e)}")
            return None, []
        except Exception as e:
            logger.warning(f"Error generating summary and passages: {str(e)}")
            return None, []

    async def _detect_category(
        self,
        llm_client,
        title: str,
        content: str,
    ) -> str:
        """Intelligently detect article category."""
        categories_str = ", ".join(self.CATEGORIES[:-1])  # Exclude "Other"

        prompt = f"""Classify the following article into ONE of these categories: {categories_str}, or Other

Article Title: {title}

Content:
{content}

Respond with ONLY the category name, nothing else."""

        try:
            response = await llm_client.generate(
                prompt=prompt,
                max_tokens=50,
                temperature=0.3,
            )

            category = response.strip().strip('.')

            # Validate category
            if category in self.CATEGORIES:
                return category

            # Try to match partial names
            for cat in self.CATEGORIES:
                if cat.lower() in category.lower() or category.lower() in cat.lower():
                    return cat

            return "Other"

        except Exception as e:
            logger.warning(f"Error detecting category: {str(e)}")
            return "Other"

    async def _generate_tags(
        self,
        llm_client,
        title: str,
        summary: str,
        category: str,
    ) -> list[str]:
        """Generate semantic tags relevant to the article."""
        prompt = f"""Generate 4-6 concise, meaningful tags for this article. Tags should be single words or short phrases that capture key concepts, technologies, or topics mentioned.

Category: {category}
Title: {title}
Summary: {summary}

Return ONLY a JSON array of strings:
["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"]"""

        try:
            response = await llm_client.generate(
                prompt=prompt,
                max_tokens=200,
                temperature=0.6,
            )

            tags = json.loads(response.strip())

            # Validate and clean tags
            if isinstance(tags, list):
                clean_tags = [
                    str(tag).strip().lower().replace(" ", "-")[:50]
                    for tag in tags
                    if isinstance(tag, str) and tag.strip()
                ]
                return clean_tags[:10]  # Max 10 tags

            return []

        except json.JSONDecodeError:
            logger.warning("Failed to parse tags JSON")
            return []
        except Exception as e:
            logger.warning(f"Error generating tags: {str(e)}")
            return []

    async def _generate_structured_markdown(
        self,
        title: str,
        author: Optional[str],
        summary: Optional[str],
        passages: list[dict],
        original_content: str,
    ) -> str:
        """Generate blog-formatted markdown using LLM to intelligently restructure content."""
        from app.integrations.llm_client import get_llm_client

        llm_client = await get_llm_client()

        # Article header
        md_parts = [f"# {title}\n"]

        # Author and metadata
        if author:
            md_parts.append(f"**By {author}**\n")

        md_parts.append("---\n")

        # Summary section - highlighted
        if summary:
            md_parts.append("## 📋 Summary\n")
            md_parts.append(f"> {summary}\n")
            md_parts.append("")

        # Overview section - key insights
        if passages:
            md_parts.append("## 🎯 Key Points\n")
            for i, passage in enumerate(passages[:3], 1):
                description = passage.get('description', '').strip()
                if description:
                    md_parts.append(f"**{i}. {description}**\n")
            md_parts.append("")

        # Full article content - use LLM to intelligently reformat
        md_parts.append("## 📝 Full Article\n")

        # Truncate content if too long for LLM
        content_for_llm = original_content[:3000] if len(original_content) > 3000 else original_content

        prompt = f"""You are a professional content formatter. Convert the following raw article content into well-structured, readable blog markdown.

Original Content:
{content_for_llm}

Requirements:
1. Create logical sections with ### headers where appropriate
2. Break long paragraphs into readable chunks (2-3 sentences each)
3. Use proper markdown formatting
4. Maintain the original meaning and flow
5. Use bullet points where content is list-like
6. Emphasize key phrases with **bold** where relevant
7. Include blockquotes for important quotes or statements
8. Do NOT include the title or summary - just the article body
9. Format as pure markdown (no HTML)
10. Return ONLY the formatted markdown, nothing else

Output: Well-formatted markdown article content"""

        try:
            formatted_content = await llm_client.generate(
                prompt=prompt,
                max_tokens=2000,
                temperature=0.5,
            )

            md_parts.append(formatted_content)

            # Add continuation note if content was truncated
            if len(original_content) > 3000:
                md_parts.append("\n---\n")
                md_parts.append("*[Article continues in full on the original source]*\n")

        except Exception as e:
            logger.warning(f"LLM markdown formatting failed: {str(e)}. Using fallback formatting.")
            # Fallback: Basic paragraph formatting
            paragraphs = [p.strip() for p in original_content.split("\n\n") if p.strip()]
            for para in paragraphs[:50]:
                if len(para.strip()) >= 10:
                    md_parts.append(f"{para}\n\n")

        return "\n".join(md_parts)
