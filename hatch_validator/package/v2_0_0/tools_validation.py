"""Tools validation strategy for v2.0.0.

This module provides the tools validation strategy for schema version 2.0.0.
It validates tool declarations and ensures that tool metadata uses the
new `desc` field instead of the legacy `description` field.
"""

import ast
import logging
from typing import Dict, List, Tuple, Set

from hatch_validator.core.validation_strategy import ToolsValidationStrategy
from hatch_validator.core.validation_context import ValidationContext

# Configure logging
logger = logging.getLogger("hatch.schema.v2_0_0.tools_validation")


class ToolsValidation(ToolsValidationStrategy):
    """Strategy for validating tools for v2.0.0."""

    def validate_tools(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate tools according to v2.0.0 schema."""
        tools = metadata.get('tools', [])
        if not tools:
            logger.debug("No tools declared in metadata")
            return True, []

        entry_point = metadata.get('entry_point')
        if not entry_point or not isinstance(entry_point, dict):
            logger.error("Dual entry point configuration required for tool validation")
            return False, ["Dual entry point configuration required for tool validation"]

        mcp_server_file = entry_point.get('mcp_server')
        if not mcp_server_file:
            logger.error("FastMCP server file not specified in entry point")
            return False, ["FastMCP server file not specified in entry point"]

        if not context.package_dir:
            logger.error("Package directory not provided for tool validation")
            return False, ["Package directory not provided for tool validation"]

        server_tools, extraction_errors = self._extract_fastmcp_tools(mcp_server_file, context)
        if extraction_errors:
            logger.error(f"Failed to extract tools from FastMCP server: {extraction_errors}")
            return False, extraction_errors

        missing_tools = []
        deprecated_fields = []
        for tool in tools:
            if 'description' in tool:
                deprecated_fields.append(
                    "Tool metadata uses deprecated 'description' field; use 'desc' instead"
                )

            tool_name = tool.get('name')
            if not tool_name:
                logger.error(f"Tool metadata missing name: {tool}")
                missing_tools.append("Tool missing name in metadata")
                continue

            if tool_name not in server_tools:
                logger.error(f"Tool '{tool_name}' not found in FastMCP server '{mcp_server_file}'")
                missing_tools.append(f"Tool '{tool_name}' not found in FastMCP server '{mcp_server_file}'")

        errors = missing_tools + deprecated_fields
        if errors:
            if missing_tools:
                errors.append(
                    "Tools must be defined in FastMCP server to ensure availability when imported independently"
                )
            return False, errors

        logger.debug(f"All {len(tools)} declared tools found in FastMCP server")
        return True, []

    def _extract_fastmcp_tools(self, server_file: str, context: ValidationContext) -> Tuple[Set[str], List[str]]:
        """Extract tool names from @mcp.tool() decorators in FastMCP server file."""
        try:
            file_path = context.package_dir / server_file
            if not file_path.exists():
                error_msg = f"FastMCP server file '{server_file}' not found"
                logger.error(error_msg)
                return set(), [error_msg]

            with open(file_path, 'r', encoding='utf-8') as f:
                source_code = f.read()

            tree = ast.parse(source_code)
            tool_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    for decorator in node.decorator_list:
                        if self._is_mcp_tool_decorator(decorator):
                            tool_names.add(node.name)
                            logger.debug(f"Found tool '{node.name}' in FastMCP server")
                            break

            logger.debug(f"Extracted {len(tool_names)} tools from FastMCP server: {tool_names}")
            return tool_names, []

        except SyntaxError as e:
            error_msg = f"Syntax error in FastMCP server '{server_file}' at line {e.lineno}: {e.msg}"
            logger.error(error_msg)
            return set(), [error_msg]
        except FileNotFoundError:
            error_msg = f"FastMCP server file '{server_file}' not found"
            logger.error(error_msg)
            return set(), [error_msg]
        except Exception as e:
            error_msg = f"Error parsing FastMCP server '{server_file}': {str(e)}"
            logger.error(error_msg)
            return set(), [error_msg]

    def _is_mcp_tool_decorator(self, decorator) -> bool:
        """Check if decorator is @mcp.tool() or @mcp.tool."""
        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                return (
                    decorator.func.attr == 'tool' and
                    isinstance(decorator.func.value, ast.Name) and
                    decorator.func.value.id == 'mcp'
                )

        if isinstance(decorator, ast.Attribute):
            return (
                decorator.attr == 'tool' and
                isinstance(decorator.value, ast.Name) and
                decorator.value.id == 'mcp'
            )

        return False
