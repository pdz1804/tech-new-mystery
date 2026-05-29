"""Tool Registry for Agent Core Runtime integration.

Manages registration, lookup, validation, and invocation of tools that
the chatbot agent can use (semantic search, web search, code interpreter).

Tools are registered with LangChain-compatible definitions and stored
in a registry for access during agent workflow execution.
"""

import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel
from langchain.tools import Tool, StructuredTool

from app.tools.semantic_search_tool import SemanticSearchTool

logger = logging.getLogger(__name__)


class ToolType(str, Enum):
    """Enumeration of supported tool types."""

    SEMANTIC_SEARCH = "semantic_search"
    WEB_SEARCH = "web_search"
    CODE_INTERPRETER = "code_interpreter"


@dataclass
class ToolRegistration:
    """Metadata for a registered tool."""

    name: str
    tool_type: ToolType
    description: str
    input_schema: Dict[str, Any]
    handler: Callable
    error_handler: Optional[Callable] = None


class ToolRegistry:
    """Registry for managing chatbot agent tools.

    Provides:
    - Tool registration with validation
    - Tool lookup by name
    - Tool input validation
    - Error handling and fallbacks

    Supports three tool types:
    1. SemanticSearchTool - search articles by semantic similarity (custom, Qdrant-based)
    2. WebSearchTool - search public web (AWS built-in, requires wrapper)
    3. CodeInterpreterTool - execute code (AWS built-in, requires wrapper)
    """

    def __init__(self):
        """Initialize the tool registry."""
        self._tools: Dict[str, ToolRegistration] = {}
        self._semantic_search_tool = SemanticSearchTool()
        logger.info("Tool registry initialized")

    def register_tools(self) -> List[Tool]:
        """Register all available tools with Agent Core.

        Creates LangChain Tool objects for semantic search and registers
        declarations for Agent Core runtime tools (web search, code interpreter).

        Returns:
            List[Tool]: List of registered LangChain tools ready for agent use

        Raises:
            Exception: If tool registration fails
        """
        try:
            logger.info("Registering tools with Agent Core...")

            # Register semantic search tool (custom, Qdrant-based)
            semantic_search_tool = self._register_semantic_search_tool()

            # Register web search tool (Agent Core runtime built-in)
            web_search_tool = self._register_web_search_tool()

            # Register code interpreter tool (Agent Core runtime built-in)
            code_interpreter_tool = self._register_code_interpreter_tool()

            tools = [semantic_search_tool, web_search_tool, code_interpreter_tool]

            logger.info(f"Successfully registered {len(tools)} tools")
            return tools

        except Exception as e:
            logger.error(f"Failed to register tools: {e}", exc_info=True)
            raise

    def _register_semantic_search_tool(self) -> Tool:
        """Register semantic search tool.

        Creates a LangChain Tool for semantic article search using Qdrant embeddings.

        Returns:
            Tool: LangChain Tool for semantic search
        """
        try:
            # Get tool definition from semantic search tool
            tool_def = self._semantic_search_tool.get_tool_definition()

            # Create input schema as Pydantic model for validation
            class SemanticSearchInput(BaseModel):
                query: str
                top_k: int = 10
                min_score: float = 0.0
                filters: Optional[Dict[str, Any]] = None

            # Create LangChain StructuredTool
            tool = StructuredTool.from_function(
                func=self._semantic_search_tool.execute,
                name=tool_def["name"],
                description=tool_def["description"],
                args_schema=SemanticSearchInput,
            )

            # Register in internal registry
            self._tools[tool_def["name"]] = ToolRegistration(
                name=tool_def["name"],
                tool_type=ToolType.SEMANTIC_SEARCH,
                description=tool_def["description"],
                input_schema=tool_def["input_schema"],
                handler=self._semantic_search_tool.execute,
                error_handler=self._handle_semantic_search_error,
            )

            logger.info(f"Registered tool: {tool_def['name']}")
            return tool

        except Exception as e:
            logger.error(f"Failed to register semantic search tool: {e}", exc_info=True)
            raise

    def _register_web_search_tool(self) -> Tool:
        """Register web search tool.

        Creates a LangChain declaration for web search.
        The actual execution is handled by Agent Core Runtime's built-in browser tool.

        Returns:
            Tool: LangChain Tool for web search
        """
        try:

            class WebSearchInput(BaseModel):
                query: str
                max_results: int = 10

            async def web_search_handler(query: str, max_results: int = 10) -> str:
                """Runtime-owned tool; invoke through AgentCoreClient streaming."""
                raise RuntimeError(
                    "web_search is executed by the Agent Core runtime; "
                    "call AgentCoreClient.invoke_agent instead of invoking it locally"
                )

            tool = StructuredTool.from_function(
                func=web_search_handler,
                name="web_search",
                description=(
                    "Search the public web for current information using AWS Browser Tool. "
                    "Returns search results from search engines and web pages."
                ),
                args_schema=WebSearchInput,
            )

            # Register in internal registry
            self._tools["web_search"] = ToolRegistration(
                name="web_search",
                tool_type=ToolType.WEB_SEARCH,
                description=tool.description,
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query text",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 10)",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
                handler=web_search_handler,
                error_handler=self._handle_web_search_error,
            )

            logger.info("Registered tool: web_search")
            return tool

        except Exception as e:
            logger.error(f"Failed to register web search tool: {e}", exc_info=True)
            raise

    def _register_code_interpreter_tool(self) -> Tool:
        """Register code interpreter tool.

        Creates a LangChain declaration for code execution.
        The actual execution is handled by Agent Core Runtime's built-in code interpreter.

        Returns:
            Tool: LangChain Tool for code interpretation
        """
        try:

            class CodeInterpreterInput(BaseModel):
                code: str
                language: str = "python"

            async def code_interpreter_handler(code: str, language: str = "python") -> str:
                """Runtime-owned tool; invoke through AgentCoreClient streaming."""
                raise RuntimeError(
                    "code_interpreter is executed by the Agent Core runtime; "
                    "call AgentCoreClient.invoke_agent instead of invoking it locally"
                )

            tool = StructuredTool.from_function(
                func=code_interpreter_handler,
                name="code_interpreter",
                description=(
                    "Execute Python, JavaScript, or TypeScript code for analysis, "
                    "calculations, and data visualization using AWS Code Interpreter."
                ),
                args_schema=CodeInterpreterInput,
            )

            # Register in internal registry
            self._tools["code_interpreter"] = ToolRegistration(
                name="code_interpreter",
                tool_type=ToolType.CODE_INTERPRETER,
                description=tool.description,
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code to execute",
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language (python, javascript, typescript)",
                            "default": "python",
                        },
                    },
                    "required": ["code"],
                },
                handler=code_interpreter_handler,
                error_handler=self._handle_code_interpreter_error,
            )

            logger.info("Registered tool: code_interpreter")
            return tool

        except Exception as e:
            logger.error(f"Failed to register code interpreter tool: {e}", exc_info=True)
            raise

    def get_tool(self, name: str) -> Optional[ToolRegistration]:
        """Get a registered tool by name.

        Args:
            name: Tool name (e.g., 'semantic_search', 'web_search', 'code_interpreter')

        Returns:
            ToolRegistration if found, None otherwise
        """
        if name not in self._tools:
            logger.warning(f"Tool not found: {name}")
            return None

        return self._tools[name]

    def validate_tool_input(self, tool_name: str, input_data: Dict[str, Any]) -> bool:
        """Validate input for a specific tool.

        Checks that input_data matches the tool's expected input_schema.

        Args:
            tool_name: Name of the tool to validate for
            input_data: Input dictionary to validate

        Returns:
            bool: True if input is valid, False otherwise
        """
        tool = self.get_tool(tool_name)
        if not tool:
            logger.error(f"Cannot validate: tool '{tool_name}' not found")
            return False

        try:
            # Check required fields
            required = tool.input_schema.get("required", [])
            for field in required:
                if field not in input_data:
                    logger.warning(f"Missing required field '{field}' for tool '{tool_name}'")
                    return False

            # Check field types
            properties = tool.input_schema.get("properties", {})
            for field, value in input_data.items():
                if field not in properties:
                    logger.warning(f"Unknown field '{field}' for tool '{tool_name}'")
                    return False

                # Type checking
                expected_type = properties[field].get("type")
                if expected_type and not self._check_type(value, expected_type):
                    logger.warning(
                        f"Invalid type for field '{field}': "
                        f"expected {expected_type}, got {type(value).__name__}"
                    )
                    return False

            logger.debug(f"Input validation passed for tool '{tool_name}'")
            return True

        except Exception as e:
            logger.error(f"Validation error for tool '{tool_name}': {e}")
            return False

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if a value matches the expected JSON schema type.

        Args:
            value: Value to check
            expected_type: Expected type string (string, number, integer, boolean, object, array)

        Returns:
            bool: True if type matches, False otherwise
        """
        type_mapping = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "object": dict,
            "array": list,
        }

        expected_python_type = type_mapping.get(expected_type)
        if not expected_python_type:
            return True  # Unknown type, assume valid

        return isinstance(value, expected_python_type)

    async def invoke_tool(
        self, tool_name: str, input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Invoke a tool with given input.

        Validates input, executes tool, and handles errors.

        Args:
            tool_name: Name of tool to invoke
            input_data: Input dictionary for the tool

        Returns:
            Dict with result or error information

        Raises:
            ValueError: If tool not found or input validation fails
        """
        # Validate input
        if not self.validate_tool_input(tool_name, input_data):
            raise ValueError(f"Invalid input for tool '{tool_name}'")

        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool not found: {tool_name}")

        try:
            logger.info(f"Invoking tool '{tool_name}' with input: {input_data}")

            # Invoke handler
            result = await tool.handler(**input_data)

            logger.info(f"Tool '{tool_name}' executed successfully")
            return {"success": True, "data": result}

        except Exception as e:
            logger.error(f"Tool '{tool_name}' execution failed: {e}", exc_info=True)

            # Try error handler if available
            if tool.error_handler:
                try:
                    fallback_result = await tool.error_handler(tool_name, input_data, e)
                    return {"success": False, "error": str(e), "fallback": fallback_result}
                except Exception as eh:
                    logger.error(f"Error handler failed: {eh}")

            return {"success": False, "error": str(e)}

    # Error handlers for tools

    async def _handle_semantic_search_error(
        self, tool_name: str, input_data: Dict[str, Any], error: Exception
    ) -> str:
        """Handle semantic search tool errors.

        Args:
            tool_name: Name of the tool (for logging)
            input_data: Original input data
            error: The exception that occurred

        Returns:
            str: Fallback message explaining the error
        """
        logger.warning(f"Semantic search failed, returning error message")
        return f"Semantic search temporarily unavailable: {str(error)}"

    async def _handle_web_search_error(
        self, tool_name: str, input_data: Dict[str, Any], error: Exception
    ) -> str:
        """Handle web search tool errors.

        Args:
            tool_name: Name of the tool (for logging)
            input_data: Original input data
            error: The exception that occurred

        Returns:
            str: Fallback message explaining the error
        """
        logger.warning(f"Web search failed, returning error message")
        return f"Web search temporarily unavailable: {str(error)}"

    async def _handle_code_interpreter_error(
        self, tool_name: str, input_data: Dict[str, Any], error: Exception
    ) -> str:
        """Handle code interpreter tool errors.

        Args:
            tool_name: Name of the tool (for logging)
            input_data: Original input data
            error: The exception that occurred

        Returns:
            str: Fallback message explaining the error
        """
        logger.warning(f"Code interpreter failed, returning error message")
        return f"Code interpreter temporarily unavailable: {str(error)}"

    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools.

        Returns:
            List of tool information dictionaries
        """
        return [
            {
                "name": tool.name,
                "type": tool.tool_type.value,
                "description": tool.description,
            }
            for tool in self._tools.values()
        ]

    def get_session_tools(self, session_id: str) -> List[Tool]:
        """Get tools available for a session.

        Currently returns all registered tools. Can be extended to
        implement per-session tool restrictions based on user permissions.

        Args:
            session_id: Session ID (for future permission checks)

        Returns:
            List[Tool]: All available tools for this session
        """
        # For now, all tools available to all sessions
        # Future: implement ACL/permission checks per session
        logger.debug(f"Loading tools for session {session_id}")
        return list(self._tools.keys())
