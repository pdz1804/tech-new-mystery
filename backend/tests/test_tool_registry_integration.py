"""Integration tests for Tool Registry with Agent Core (CHT-009).

Tests tool registration and invocation with real Agent Core workflow.
Requires running backend with Qdrant and embedding service.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List

from app.integrations.tool_registry import ToolRegistry, ToolType
from app.models.search_result import ArticleResult


@pytest.fixture
def tool_registry():
    """Create a tool registry for integration tests."""
    return ToolRegistry()


class TestToolRegistrationWithAgent:
    """Test tool registration for agent workflow."""

    def test_register_tools_for_agent_use(self, tool_registry):
        """Test that registered tools can be used with LangChain agent."""
        tools = tool_registry.register_tools()

        # Verify tools are LangChain Tools
        from langchain.tools import Tool, StructuredTool

        for tool in tools:
            assert isinstance(tool, (Tool, StructuredTool))
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "func")

    def test_agent_can_access_all_tools(self, tool_registry):
        """Test that agent workflow can access all registered tools."""
        tools = tool_registry.register_tools()
        tool_names = {tool.name for tool in tools}

        assert "semantic_search" in tool_names
        assert "web_search" in tool_names
        assert "code_interpreter" in tool_names

        # Verify each tool has proper callable
        for tool in tools:
            assert callable(tool.func)

    def test_tools_have_proper_schemas(self, tool_registry):
        """Test that tools have proper input schemas for agent binding."""
        tools = tool_registry.register_tools()

        for tool in tools:
            # Check for StructuredTool which requires args_schema
            if hasattr(tool, "args_schema"):
                assert tool.args_schema is not None
                # Should have properties defined
                if hasattr(tool.args_schema, "schema"):
                    schema = tool.args_schema.schema()
                    assert "properties" in schema or hasattr(
                        tool.args_schema, "__fields__"
                    )


@pytest.mark.asyncio
class TestSemanticSearchIntegration:
    """Integration tests for semantic search tool."""

    async def test_semantic_search_tool_callable(self, tool_registry):
        """Test that semantic search tool handler is callable."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("semantic_search")

        assert tool is not None
        assert callable(tool.handler)

    async def test_semantic_search_with_real_embedding_service(self, tool_registry):
        """Test semantic search with mock Qdrant service.

        This test verifies that the semantic search tool properly
        integrates with the embedding and Qdrant services.
        """
        with patch("app.tools.semantic_search_tool.QdrantService") as mock_qdrant, \
             patch("app.tools.semantic_search_tool.EmbeddingService") as mock_embedding, \
             patch("app.tools.semantic_search_tool.ArticleRepository") as mock_repo:

            # Mock embedding service
            mock_embedding_instance = AsyncMock()
            mock_embedding_instance.generate_embedding = AsyncMock(
                return_value=[0.1] * 1536
            )
            mock_embedding.return_value = mock_embedding_instance

            # Mock Qdrant service
            mock_qdrant_instance = MagicMock()
            mock_qdrant_instance.client = MagicMock()
            mock_qdrant_instance.collection_name = "test_collection"

            # Create mock search results
            mock_point = MagicMock()
            mock_point.payload = {
                "article_id": "article-123",
                "slug": "test-article",
                "title": "Test Article",
                "summary": "Test summary",
                "category": "tech",
                "source_id": "test-source",
                "published_at": 1234567890,
            }
            mock_point.score = 0.85

            mock_qdrant_instance.client.query_points = MagicMock(
                return_value=MagicMock(points=[mock_point])
            )
            mock_qdrant.return_value = mock_qdrant_instance

            # Mock article repository
            mock_repo_instance = AsyncMock()
            mock_article = MagicMock()
            mock_article.title = "Test Article"
            mock_article.summary = "Test summary"
            mock_article.source_id = "test-source"
            mock_article.original_url = "https://test.com"
            mock_article.published_at = 1234567890
            mock_article.author = "Test Author"
            mock_article.category = "tech"
            mock_article.view_count = 100
            mock_article.like_count = 10
            mock_repo_instance.get_by_id = AsyncMock(return_value=mock_article)
            mock_repo.return_value = mock_repo_instance

            # Re-create tool registry with mocked services
            tool_registry_test = ToolRegistry()

            # Test semantic search
            results = await tool_registry_test._semantic_search_tool.execute(
                query="test query"
            )

            assert isinstance(results, list)
            # Verify embedding was called
            mock_embedding_instance.generate_embedding.assert_called_once()

    async def test_semantic_search_validate_output_format(self, tool_registry):
        """Test that semantic search returns properly formatted results."""
        with patch("app.tools.semantic_search_tool.QdrantService") as mock_qdrant, \
             patch("app.tools.semantic_search_tool.EmbeddingService") as mock_embedding, \
             patch("app.tools.semantic_search_tool.ArticleRepository") as mock_repo:

            # Setup mocks
            mock_embedding_instance = AsyncMock()
            mock_embedding_instance.generate_embedding = AsyncMock(
                return_value=[0.1] * 1536
            )
            mock_embedding.return_value = mock_embedding_instance

            mock_qdrant_instance = MagicMock()
            mock_qdrant_instance.client = MagicMock()
            mock_qdrant_instance.collection_name = "test_collection"

            mock_point = MagicMock()
            mock_point.payload = {
                "article_id": "article-123",
                "slug": "test",
                "title": "Test",
                "summary": "Summary",
                "category": "tech",
                "source_id": "source",
                "published_at": 1234567890,
            }
            mock_point.score = 0.85

            mock_qdrant_instance.client.query_points = MagicMock(
                return_value=MagicMock(points=[mock_point])
            )
            mock_qdrant.return_value = mock_qdrant_instance

            mock_repo_instance = AsyncMock()
            mock_article = MagicMock()
            mock_article.title = "Test"
            mock_article.summary = "Summary"
            mock_article.source_id = "source"
            mock_article.original_url = "https://test.com"
            mock_article.published_at = 1234567890
            mock_article.author = "Author"
            mock_article.category = "tech"
            mock_article.view_count = 100
            mock_article.like_count = 10
            mock_repo_instance.get_by_id = AsyncMock(return_value=mock_article)
            mock_repo.return_value = mock_repo_instance

            tool_registry_test = ToolRegistry()
            results = await tool_registry_test._semantic_search_tool.execute(
                query="test"
            )

            assert isinstance(results, list)
            if results:
                result = results[0]
                assert isinstance(result, ArticleResult)
                assert hasattr(result, "article_id")
                assert hasattr(result, "title")
                assert hasattr(result, "relevance_score")
                assert hasattr(result, "source")


@pytest.mark.asyncio
class TestWebSearchIntegration:
    """Integration tests for web search tool."""

    async def test_web_search_handler_callable(self, tool_registry):
        """Test that web search handler is callable."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("web_search")

        assert tool is not None
        assert callable(tool.handler)

    async def test_web_search_handler_returns_string(self, tool_registry):
        """Test that web search handler returns a string result."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("web_search")

        # Call the handler
        result = await tool.handler(query="test query", max_results=10)

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_web_search_with_different_max_results(self, tool_registry):
        """Test web search with different max_results values."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("web_search")

        for max_results in [5, 10, 20]:
            result = await tool.handler(query="test", max_results=max_results)
            assert isinstance(result, str)
            assert str(max_results) in result


@pytest.mark.asyncio
class TestCodeInterpreterIntegration:
    """Integration tests for code interpreter tool."""

    async def test_code_interpreter_handler_callable(self, tool_registry):
        """Test that code interpreter handler is callable."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("code_interpreter")

        assert tool is not None
        assert callable(tool.handler)

    async def test_code_interpreter_handler_returns_string(self, tool_registry):
        """Test that code interpreter handler returns a string result."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("code_interpreter")

        code = "x = 1 + 1; print(x)"
        result = await tool.handler(code=code, language="python")

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_code_interpreter_with_different_languages(self, tool_registry):
        """Test code interpreter with different languages."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("code_interpreter")

        languages = ["python", "javascript", "typescript"]

        for lang in languages:
            result = await tool.handler(code="test", language=lang)
            assert isinstance(result, str)
            assert lang in result


@pytest.mark.asyncio
class TestToolInvocationWorkflow:
    """Test complete tool invocation workflow."""

    async def test_invoke_semantic_search_through_registry(self, tool_registry):
        """Test invoking semantic search through registry."""
        tool_registry.register_tools()

        # Mock the semantic search handler
        tool_registry._tools["semantic_search"].handler = AsyncMock(return_value=[])

        result = await tool_registry.invoke_tool(
            "semantic_search", {"query": "AI breakthroughs"}
        )

        assert result["success"] is True

    async def test_invoke_web_search_through_registry(self, tool_registry):
        """Test invoking web search through registry."""
        tool_registry.register_tools()

        result = await tool_registry.invoke_tool(
            "web_search", {"query": "latest news"}
        )

        assert result["success"] is True

    async def test_invoke_code_interpreter_through_registry(self, tool_registry):
        """Test invoking code interpreter through registry."""
        tool_registry.register_tools()

        result = await tool_registry.invoke_tool(
            "code_interpreter", {"code": "print('hello')"}
        )

        assert result["success"] is True

    async def test_tool_invocation_with_error_handling(self, tool_registry):
        """Test tool invocation with proper error handling."""
        tool_registry.register_tools()

        # Make handler fail
        tool_registry._tools["semantic_search"].handler = AsyncMock(
            side_effect=Exception("Service unavailable")
        )

        result = await tool_registry.invoke_tool(
            "semantic_search", {"query": "test"}
        )

        assert result["success"] is False
        assert "error" in result


class TestToolRegistryPersistence:
    """Test tool registry persistence across requests."""

    def test_registry_tools_persist(self, tool_registry):
        """Test that tools persist after registration."""
        tools1 = tool_registry.register_tools()
        count1 = len(tools1)

        # Get tools again
        tools2 = tool_registry.register_tools()
        count2 = len(tools2)

        assert count1 == count2

    def test_multiple_registry_instances(self):
        """Test that multiple registry instances work independently."""
        registry1 = ToolRegistry()
        registry2 = ToolRegistry()

        tools1 = registry1.register_tools()
        tools2 = registry2.register_tools()

        assert len(tools1) == len(tools2)

        # Modify one registry
        registry1._tools.pop("web_search", None)

        assert len(registry1._tools) < len(registry2._tools)


class TestToolRegistryForAgentFramework:
    """Test integration with LangChain/LangGraph agent framework."""

    def test_tools_compatible_with_langchain_agents(self, tool_registry):
        """Test that registered tools work with LangChain agents."""
        tools = tool_registry.register_tools()

        # Verify tools are proper LangChain Tool objects
        for tool in tools:
            # These are required by create_react_agent
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "func") or hasattr(tool, "_run")

    def test_tools_have_proper_names_for_agent_binding(self, tool_registry):
        """Test that tool names are valid for agent binding."""
        tools = tool_registry.register_tools()

        valid_name_pattern = r"^[a-z_][a-z0-9_]*$"
        import re

        for tool in tools:
            assert re.match(valid_name_pattern, tool.name), \
                f"Tool name '{tool.name}' invalid for agent binding"

    def test_tools_have_unique_names(self, tool_registry):
        """Test that all tools have unique names."""
        tools = tool_registry.register_tools()
        names = [tool.name for tool in tools]

        assert len(names) == len(set(names)), "Duplicate tool names found"


class TestToolRegistryErrorCases:
    """Test error handling in tool registry."""

    def test_registry_handles_missing_semantic_search_service(self):
        """Test registry handles missing embedding service gracefully."""
        with patch("app.integrations.tool_registry.SemanticSearchTool") as mock_tool:
            mock_tool.side_effect = Exception("Service unavailable")

            with pytest.raises(Exception):
                registry = ToolRegistry()
                registry.register_tools()

    @pytest.mark.asyncio
    async def test_tool_invocation_with_invalid_input_type(self, tool_registry):
        """Test tool invocation rejects invalid input types."""
        tool_registry.register_tools()

        with pytest.raises(ValueError):
            await tool_registry.invoke_tool(
                "semantic_search",
                {"query": 123}  # Should be string
            )

    @pytest.mark.asyncio
    async def test_tool_invocation_with_missing_required_field(self, tool_registry):
        """Test tool invocation rejects missing required fields."""
        tool_registry.register_tools()

        with pytest.raises(ValueError):
            await tool_registry.invoke_tool(
                "semantic_search",
                {}  # Missing required 'query'
            )


class TestToolRegistrySessionManagement:
    """Test session-aware tool management."""

    def test_get_session_tools_returns_all_tools(self, tool_registry):
        """Test that sessions have access to all tools."""
        tool_registry.register_tools()

        session_tools = tool_registry.get_session_tools("session-abc123")

        assert len(session_tools) >= 3
        assert all(isinstance(t, str) for t in session_tools)

    def test_different_sessions_get_same_tools(self, tool_registry):
        """Test tool consistency across sessions."""
        tool_registry.register_tools()

        session1_tools = tool_registry.get_session_tools("session-1")
        session2_tools = tool_registry.get_session_tools("session-2")

        assert session1_tools == session2_tools
