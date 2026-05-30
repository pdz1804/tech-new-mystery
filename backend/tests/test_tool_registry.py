"""Unit tests for Tool Registry (CHT-009).

Tests tool registration, lookup, validation, and invocation.
"""

import pytest
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from app.integrations.tool_registry import ToolRegistry, ToolType, ToolRegistration


@pytest.fixture
def tool_registry():
    """Create a fresh tool registry for testing."""
    return ToolRegistry()


class TestToolRegistryBasics:
    """Test basic tool registry functionality."""

    def test_registry_initialization(self, tool_registry):
        """Test that registry initializes properly."""
        assert tool_registry is not None
        assert isinstance(tool_registry._tools, dict)
        assert tool_registry._semantic_search_tool is not None

    def test_register_tools_returns_list(self, tool_registry):
        """Test that register_tools returns a list of tools."""
        tools = tool_registry.register_tools()
        assert isinstance(tools, list)
        assert len(tools) >= 3  # At least 3 tools registered
        assert len(tools) == len(tool_registry._tools)

    def test_all_three_tools_registered(self, tool_registry):
        """Test that all three tools are registered."""
        tools = tool_registry.register_tools()
        tool_names = [tool.name for tool in tools]

        assert "semantic_search" in tool_names
        assert "web_search" in tool_names
        assert "code_interpreter" in tool_names

    def test_tool_names_are_strings(self, tool_registry):
        """Test that all tool names are strings."""
        tools = tool_registry.register_tools()
        for tool in tools:
            assert isinstance(tool.name, str)
            assert len(tool.name) > 0

    def test_tool_descriptions_are_strings(self, tool_registry):
        """Test that all tools have descriptions."""
        tools = tool_registry.register_tools()
        for tool in tools:
            assert hasattr(tool, "description")
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0


class TestToolLookup:
    """Test tool lookup by name."""

    def test_get_tool_semantic_search(self, tool_registry):
        """Test retrieving semantic search tool."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("semantic_search")

        assert tool is not None
        assert tool.name == "semantic_search"
        assert tool.tool_type == ToolType.SEMANTIC_SEARCH

    def test_get_tool_web_search(self, tool_registry):
        """Test retrieving web search tool."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("web_search")

        assert tool is not None
        assert tool.name == "web_search"
        assert tool.tool_type == ToolType.WEB_SEARCH

    def test_get_tool_code_interpreter(self, tool_registry):
        """Test retrieving code interpreter tool."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("code_interpreter")

        assert tool is not None
        assert tool.name == "code_interpreter"
        assert tool.tool_type == ToolType.CODE_INTERPRETER

    def test_get_nonexistent_tool(self, tool_registry):
        """Test getting a tool that doesn't exist."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("nonexistent_tool")

        assert tool is None

    def test_get_tool_returns_registration(self, tool_registry):
        """Test that get_tool returns ToolRegistration object."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("semantic_search")

        assert isinstance(tool, ToolRegistration)
        assert hasattr(tool, "name")
        assert hasattr(tool, "tool_type")
        assert hasattr(tool, "description")
        assert hasattr(tool, "input_schema")
        assert hasattr(tool, "handler")


class TestToolInputValidation:
    """Test tool input validation."""

    def test_validate_semantic_search_valid_input(self, tool_registry):
        """Test validating valid semantic search input."""
        tool_registry.register_tools()

        input_data = {"query": "AI breakthroughs"}
        result = tool_registry.validate_tool_input("semantic_search", input_data)

        assert result is True

    def test_validate_semantic_search_with_optional_params(self, tool_registry):
        """Test semantic search with optional parameters."""
        tool_registry.register_tools()

        input_data = {
            "query": "AI breakthroughs",
            "top_k": 5,
            "min_score": 0.7,
        }
        result = tool_registry.validate_tool_input("semantic_search", input_data)

        assert result is True

    def test_validate_semantic_search_missing_required_field(self, tool_registry):
        """Test semantic search validation fails without required field."""
        tool_registry.register_tools()

        input_data = {"top_k": 5}  # Missing required 'query'
        result = tool_registry.validate_tool_input("semantic_search", input_data)

        assert result is False

    def test_validate_semantic_search_wrong_type(self, tool_registry):
        """Test semantic search validation fails with wrong field type."""
        tool_registry.register_tools()

        input_data = {"query": 123}  # Should be string, not int
        result = tool_registry.validate_tool_input("semantic_search", input_data)

        assert result is False

    def test_validate_web_search_valid_input(self, tool_registry):
        """Test validating valid web search input."""
        tool_registry.register_tools()

        input_data = {"query": "latest AI news"}
        result = tool_registry.validate_tool_input("web_search", input_data)

        assert result is True

    def test_validate_web_search_with_max_results(self, tool_registry):
        """Test web search with max_results parameter."""
        tool_registry.register_tools()

        input_data = {"query": "latest AI news", "max_results": 20}
        result = tool_registry.validate_tool_input("web_search", input_data)

        assert result is True

    def test_validate_code_interpreter_valid_input(self, tool_registry):
        """Test validating valid code interpreter input."""
        tool_registry.register_tools()

        input_data = {"code": "print('hello')"}
        result = tool_registry.validate_tool_input("code_interpreter", input_data)

        assert result is True

    def test_validate_code_interpreter_with_language(self, tool_registry):
        """Test code interpreter with language parameter."""
        tool_registry.register_tools()

        input_data = {
            "code": "console.log('hello')",
            "language": "javascript",
        }
        result = tool_registry.validate_tool_input("code_interpreter", input_data)

        assert result is True

    def test_validate_nonexistent_tool(self, tool_registry):
        """Test validation for non-existent tool."""
        tool_registry.register_tools()

        input_data = {"query": "test"}
        result = tool_registry.validate_tool_input("nonexistent_tool", input_data)

        assert result is False

    def test_validate_empty_query_string(self, tool_registry):
        """Test validation allows empty string (schema doesn't forbid it)."""
        tool_registry.register_tools()

        input_data = {"query": ""}
        result = tool_registry.validate_tool_input("semantic_search", input_data)

        # Schema allows empty string, but semantic search handler will reject it
        assert result is True


class TestToolTypeChecking:
    """Test the _check_type helper method."""

    def test_check_type_string(self, tool_registry):
        """Test type checking for string."""
        assert tool_registry._check_type("hello", "string") is True
        assert tool_registry._check_type(123, "string") is False

    def test_check_type_integer(self, tool_registry):
        """Test type checking for integer."""
        assert tool_registry._check_type(123, "integer") is True
        assert tool_registry._check_type("123", "integer") is False

    def test_check_type_number(self, tool_registry):
        """Test type checking for number."""
        assert tool_registry._check_type(123, "number") is True
        assert tool_registry._check_type(123.45, "number") is True
        assert tool_registry._check_type("123", "number") is False

    def test_check_type_boolean(self, tool_registry):
        """Test type checking for boolean."""
        assert tool_registry._check_type(True, "boolean") is True
        assert tool_registry._check_type(False, "boolean") is True
        assert tool_registry._check_type(1, "boolean") is False

    def test_check_type_object(self, tool_registry):
        """Test type checking for object (dict)."""
        assert tool_registry._check_type({"key": "value"}, "object") is True
        assert tool_registry._check_type("string", "object") is False

    def test_check_type_array(self, tool_registry):
        """Test type checking for array (list)."""
        assert tool_registry._check_type([1, 2, 3], "array") is True
        assert tool_registry._check_type("string", "array") is False


class TestListTools:
    """Test listing registered tools."""

    def test_list_tools_returns_list(self, tool_registry):
        """Test that list_tools returns a list."""
        tool_registry.register_tools()
        tools_list = tool_registry.list_tools()

        assert isinstance(tools_list, list)
        assert len(tools_list) >= 3

    def test_list_tools_contains_all_tools(self, tool_registry):
        """Test that list contains all registered tools."""
        tool_registry.register_tools()
        tools_list = tool_registry.list_tools()
        tool_names = [t["name"] for t in tools_list]

        assert "semantic_search" in tool_names
        assert "web_search" in tool_names
        assert "code_interpreter" in tool_names

    def test_list_tools_item_structure(self, tool_registry):
        """Test that each tool item has required fields."""
        tool_registry.register_tools()
        tools_list = tool_registry.list_tools()

        for tool in tools_list:
            assert "name" in tool
            assert "type" in tool
            assert "description" in tool
            assert isinstance(tool["name"], str)
            assert isinstance(tool["type"], str)
            assert isinstance(tool["description"], str)


class TestGetSessionTools:
    """Test getting tools for a session."""

    def test_get_session_tools_returns_list(self, tool_registry):
        """Test that get_session_tools returns a list."""
        tool_registry.register_tools()
        tools = tool_registry.get_session_tools("session-123")

        assert isinstance(tools, list)
        assert len(tools) >= 3

    def test_get_session_tools_includes_all_tools(self, tool_registry):
        """Test that session has access to all registered tools."""
        tool_registry.register_tools()
        tools = tool_registry.get_session_tools("session-123")

        assert "semantic_search" in tools
        assert "web_search" in tools
        assert "code_interpreter" in tools

    def test_get_session_tools_for_different_sessions(self, tool_registry):
        """Test that different sessions get the same tools."""
        tool_registry.register_tools()
        tools1 = tool_registry.get_session_tools("session-1")
        tools2 = tool_registry.get_session_tools("session-2")

        assert tools1 == tools2


class TestSemanticSearchTool:
    """Test semantic search tool specifics."""

    def test_semantic_search_tool_has_execute_handler(self, tool_registry):
        """Test that semantic search tool has execute handler."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("semantic_search")

        assert tool is not None
        assert tool.handler is not None
        assert callable(tool.handler)

    def test_semantic_search_tool_has_error_handler(self, tool_registry):
        """Test that semantic search tool has error handler."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("semantic_search")

        assert tool is not None
        assert tool.error_handler is not None
        assert callable(tool.error_handler)

    def test_semantic_search_input_schema_has_query(self, tool_registry):
        """Test that semantic search input schema includes query."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("semantic_search")

        schema = tool.input_schema
        assert "query" in schema.get("properties", {})
        assert "query" in schema.get("required", [])

    def test_semantic_search_input_schema_has_optional_params(self, tool_registry):
        """Test that semantic search includes optional parameters."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("semantic_search")

        schema = tool.input_schema
        properties = schema.get("properties", {})

        assert "top_k" in properties
        assert "min_score" in properties
        assert "filters" in properties


class TestWebSearchTool:
    """Test web search tool specifics."""

    def test_web_search_tool_has_handler(self, tool_registry):
        """Test that web search tool has handler."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("web_search")

        assert tool is not None
        assert tool.handler is not None
        assert callable(tool.handler)

    def test_web_search_tool_has_error_handler(self, tool_registry):
        """Test that web search tool has error handler."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("web_search")

        assert tool is not None
        assert tool.error_handler is not None

    def test_web_search_input_schema_structure(self, tool_registry):
        """Test that web search input schema is properly structured."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("web_search")

        schema = tool.input_schema
        assert "properties" in schema
        assert "required" in schema
        assert "query" in schema["properties"]
        assert "query" in schema["required"]


class TestCodeInterpreterTool:
    """Test code interpreter tool specifics."""

    def test_code_interpreter_tool_has_handler(self, tool_registry):
        """Test that code interpreter tool has handler."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("code_interpreter")

        assert tool is not None
        assert tool.handler is not None
        assert callable(tool.handler)

    def test_code_interpreter_tool_has_error_handler(self, tool_registry):
        """Test that code interpreter tool has error handler."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("code_interpreter")

        assert tool is not None
        assert tool.error_handler is not None

    def test_code_interpreter_input_schema_structure(self, tool_registry):
        """Test that code interpreter input schema is properly structured."""
        tool_registry.register_tools()
        tool = tool_registry.get_tool("code_interpreter")

        schema = tool.input_schema
        assert "properties" in schema
        assert "required" in schema
        assert "code" in schema["properties"]
        assert "code" in schema["required"]


@pytest.mark.asyncio
class TestToolInvocation:
    """Test tool invocation."""

    async def test_invoke_tool_with_valid_input(self, tool_registry):
        """Test invoking tool with valid input."""
        tool_registry.register_tools()

        # Mock the semantic search handler
        tool_registry._tools["semantic_search"].handler = AsyncMock(
            return_value=[]
        )

        result = await tool_registry.invoke_tool(
            "semantic_search",
            {"query": "test"}
        )

        assert result["success"] is True
        assert "data" in result

    async def test_invoke_tool_invalid_input(self, tool_registry):
        """Test invoking tool with invalid input raises error."""
        tool_registry.register_tools()

        with pytest.raises(ValueError):
            await tool_registry.invoke_tool(
                "semantic_search",
                {"invalid_field": "test"}  # Missing required 'query'
            )

    async def test_invoke_tool_nonexistent(self, tool_registry):
        """Test invoking non-existent tool raises error."""
        tool_registry.register_tools()

        with pytest.raises(ValueError):
            await tool_registry.invoke_tool(
                "nonexistent_tool",
                {"query": "test"}
            )

    async def test_invoke_tool_with_error_handler(self, tool_registry):
        """Test that error handler is called on tool failure."""
        tool_registry.register_tools()

        # Mock handler to raise exception
        tool_registry._tools["semantic_search"].handler = AsyncMock(
            side_effect=Exception("Test error")
        )

        result = await tool_registry.invoke_tool(
            "semantic_search",
            {"query": "test"}
        )

        assert result["success"] is False
        assert "error" in result


class TestErrorHandlers:
    """Test error handling for tools."""

    @pytest.mark.asyncio
    async def test_semantic_search_error_handler(self, tool_registry):
        """Test semantic search error handler."""
        result = await tool_registry._handle_semantic_search_error(
            "semantic_search",
            {"query": "test"},
            Exception("Test error")
        )

        assert isinstance(result, str)
        assert "Semantic search" in result
        assert "unavailable" in result

    @pytest.mark.asyncio
    async def test_web_search_error_handler(self, tool_registry):
        """Test web search error handler."""
        result = await tool_registry._handle_web_search_error(
            "web_search",
            {"query": "test"},
            Exception("Test error")
        )

        assert isinstance(result, str)
        assert "Web search" in result
        assert "unavailable" in result

    @pytest.mark.asyncio
    async def test_code_interpreter_error_handler(self, tool_registry):
        """Test code interpreter error handler."""
        result = await tool_registry._handle_code_interpreter_error(
            "code_interpreter",
            {"code": "print('test')"},
            Exception("Test error")
        )

        assert isinstance(result, str)
        assert "Code interpreter" in result
        assert "unavailable" in result
