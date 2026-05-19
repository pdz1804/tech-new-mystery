"""Unit tests for ArticleProcessingService new methods."""

import pytest
from unittest.mock import patch, AsyncMock
from app.services.article_processing_service import ArticleProcessingService


@pytest.mark.asyncio
class TestArticleProcessingNewMethods:
    """Test new ArticleProcessingService methods."""

    async def test_extract_text_from_html_simple(self):
        """Test HTML text extraction with simple HTML."""
        service = ArticleProcessingService()
        html_content = """
        <html>
        <body>
            <h1>Test Title</h1>
            <p>This is test content.</p>
            <p>This is more content.</p>
        </body>
        </html>
        """

        text = service._extract_text_from_html(html_content)

        assert "Test Title" in text
        assert "This is test content." in text
        assert "This is more content." in text
        assert "<" not in text
        assert ">" not in text

    def test_extract_text_from_html_removes_scripts(self):
        """Test that script tags are removed."""
        service = ArticleProcessingService()
        html_content = """
        <html>
        <body>
            <p>Real content</p>
            <script>console.log('hidden')</script>
            <p>More content</p>
        </body>
        </html>
        """

        text = service._extract_text_from_html(html_content)

        assert "Real content" in text
        assert "More content" in text
        assert "console.log" not in text
        assert "<script>" not in text

    def test_extract_text_from_html_entities(self):
        """Test HTML entity decoding."""
        service = ArticleProcessingService()
        html_content = "<p>Hello &amp; goodbye &quot;quoted&quot;</p>"

        text = service._extract_text_from_html(html_content)

        # Check that HTML entities are decoded properly
        assert "Hello & goodbye" in text
        assert '"quoted"' in text
        assert "&amp;" not in text

    @patch("app.services.article_processing_service.get_llm_client")
    async def test_generate_title_from_content(self, mock_get_llm):
        """Test title generation from content."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="Generated Article Title")
        mock_get_llm.return_value = mock_llm

        service = ArticleProcessingService()
        content = "This is a long article about artificial intelligence and machine learning trends in 2024."

        title = await service._generate_title_from_content(mock_llm, content)

        assert title == "Generated Article Title"
        mock_llm.generate.assert_called_once()

    @patch("app.services.article_processing_service.get_llm_client")
    async def test_generate_title_from_content_empty_response(self, mock_get_llm):
        """Test title generation with empty response."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(return_value="")
        mock_get_llm.return_value = mock_llm

        service = ArticleProcessingService()
        title = await service._generate_title_from_content(mock_llm, "Some content")

        assert title == "Untitled"

    @patch("app.services.article_processing_service.get_llm_client")
    async def test_generate_title_from_content_exception(self, mock_get_llm):
        """Test title generation with exception."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock(side_effect=Exception("API error"))
        mock_get_llm.return_value = mock_llm

        service = ArticleProcessingService()
        title = await service._generate_title_from_content(mock_llm, "Some content")

        assert title == "Untitled"

    @patch("app.services.article_processing_service.get_llm_client")
    async def test_process_url_content_success(self, mock_get_llm):
        """Test successful URL content processing."""
        mock_llm = AsyncMock()
        mock_llm.generate = AsyncMock()

        # Setup responses for multiple calls
        mock_llm.generate.side_effect = [
            "AI News Article",  # title
            '{"summary": "Article summary", "passages": [{"text": "passage", "description": "desc"}]}',  # summary/passages
            "AI",  # category
            '["ai", "machine-learning", "technology"]',  # tags
        ]
        mock_get_llm.return_value = mock_llm

        service = ArticleProcessingService()
        html_content = """
        <html>
        <body>
            <article>
                <h1>AI Article Title</h1>
                <p>This is a comprehensive article about artificial intelligence.</p>
                <p>Machine learning is transforming the industry.</p>
            </article>
        </body>
        </html>
        """

        result = await service.process_url_content(
            url="https://example.com/ai-article",
            raw_content=html_content,
            title=None,
            author="John Doe"
        )

        assert result["title"] == "AI News Article"
        assert result["author"] == "John Doe"
        assert result["category"] == "AI"
        assert len(result["tags"]) > 0
        assert result["summary"] is not None

    @patch("app.services.article_processing_service.get_llm_client")
    async def test_process_url_content_short_content(self, mock_get_llm):
        """Test processing with short content."""
        mock_get_llm.return_value = AsyncMock()

        service = ArticleProcessingService()
        result = await service.process_url_content(
            url="https://example.com/short",
            raw_content="Too short",
            title="Test",
            author="Author"
        )

        assert result["title"] == "Test"
        assert result["summary"] is None
        assert result["tags"] == []
        assert result["category"] == "Other"

    @patch("app.services.article_processing_service.get_llm_client")
    async def test_process_url_content_empty_content(self, mock_get_llm):
        """Test processing with empty content."""
        mock_get_llm.return_value = AsyncMock()

        service = ArticleProcessingService()
        result = await service.process_url_content(
            url="https://example.com/empty",
            raw_content="",
            title="Provided Title",
            author=None
        )

        assert result["title"] == "Provided Title"
        assert result["author"] is None
        assert result["summary"] is None
