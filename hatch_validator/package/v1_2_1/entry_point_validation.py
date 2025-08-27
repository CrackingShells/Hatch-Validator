"""Entry point validation strategy for v1.2.1.

This module provides the entry point validation strategy for schema version 1.2.1,
which validates dual entry point configuration (FastMCP server + HatchMCP wrapper).
"""

import ast
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set

from hatch_validator.core.validation_strategy import EntryPointValidationStrategy
from hatch_validator.core.validation_context import ValidationContext


# Configure logging
logger = logging.getLogger("hatch.schema.v1_2_1.entry_point_validation")


class EntryPointValidation(EntryPointValidationStrategy):
    """Strategy for validating dual entry point files for v1.2.1.
    
    This strategy validates that both mcp_server (FastMCP server) and 
    hatch_mcp_server (HatchMCP wrapper) files exist and that the wrapper
    properly imports from the FastMCP server.
    """
    
    def validate_entry_point(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate dual entry point according to v1.2.1 schema.
        
        Args:
            metadata (Dict): Package metadata containing entry point information
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether entry point validation was successful
                - List[str]: List of entry point validation errors
        """
        entry_point = metadata.get('entry_point')
        if not entry_point:
            logger.error("No entry_point specified in metadata")
            return False, ["No entry_point specified in metadata"]
        
        # Schema validation ensures this is a dict, but double-check
        if not isinstance(entry_point, dict):
            logger.error("entry_point must be an object for schema v1.2.1")
            return False, ["entry_point must be an object for schema v1.2.1"]
        
        if not context.package_dir:
            logger.error("Package directory not provided for entry point validation")
            return False, ["Package directory not provided for entry point validation"]
        
        errors = []
        
        # Get both entry point files
        mcp_server = entry_point.get('mcp_server')
        hatch_mcp_server = entry_point.get('hatch_mcp_server')
        
        # Validate both files exist
        mcp_server_valid, mcp_server_errors = self._validate_file_exists(mcp_server, context, "FastMCP server")
        if not mcp_server_valid:
            errors.extend(mcp_server_errors)
        
        hatch_wrapper_valid, hatch_wrapper_errors = self._validate_file_exists(hatch_mcp_server, context, "HatchMCP wrapper")
        if not hatch_wrapper_valid:
            errors.extend(hatch_wrapper_errors)
        
        # Only validate import relationship if both files exist
        if mcp_server_valid and hatch_wrapper_valid:
            import_valid, import_errors = self._validate_import_relationship(
                mcp_server, hatch_mcp_server, context
            )
            if not import_valid:
                errors.extend(import_errors)
        
        if errors:
            logger.error(f"Entry point validation failed with {len(errors)} errors")
            return False, errors
        
        logger.debug("Dual entry point validation successful")
        return True, []
    
    def _validate_file_exists(self, filename: str, context: ValidationContext, file_type: str) -> Tuple[bool, List[str]]:
        """Validate that a file exists and is accessible.
        
        Args:
            filename (str): Name of the file to validate
            context (ValidationContext): Validation context with package directory
            file_type (str): Type of file for error messages
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        if not filename:
            error_msg = f"{file_type} filename not specified"
            logger.error(error_msg)
            return False, [error_msg]
        
        file_path = context.package_dir / filename
        
        if not file_path.exists():
            error_msg = f"{file_type} file '{filename}' does not exist"
            logger.error(error_msg)
            return False, [error_msg]
        
        if not file_path.is_file():
            error_msg = f"{file_type} '{filename}' is not a file"
            logger.error(error_msg)
            return False, [error_msg]
        
        # Validate it's a Python file
        if not filename.endswith('.py'):
            error_msg = f"{file_type} '{filename}' must be a Python file (.py)"
            logger.error(error_msg)
            return False, [error_msg]
        
        logger.debug(f"{file_type} file '{filename}' exists and is valid")
        return True, []
    
    def _validate_import_relationship(self, mcp_server: str, hatch_wrapper: str, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate that HatchMCP wrapper imports from FastMCP server.
        
        Args:
            mcp_server (str): FastMCP server filename
            hatch_wrapper (str): HatchMCP wrapper filename
            context (ValidationContext): Validation context with package directory
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        try:
            wrapper_path = context.package_dir / hatch_wrapper
            with open(wrapper_path, 'r', encoding='utf-8') as f:
                source_code = f.read()
            
            # Parse the wrapper file
            tree = ast.parse(source_code)
            
            # Expected import: from mcp_server import mcp (without .py extension)
            expected_module = mcp_server.replace('.py', '')
            
            # Look for the import statement
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module == expected_module:
                        # Check if 'mcp' is imported
                        for alias in node.names:
                            if alias.name == 'mcp':
                                logger.debug(f"Found valid import: from {expected_module} import mcp")
                                return True, []
            
            # If we get here, the import wasn't found
            error_msg = f"HatchMCP wrapper must import 'mcp' from '{expected_module}'"
            suggestion = f"Expected: from {expected_module} import mcp"
            logger.error(error_msg)
            return False, [error_msg, suggestion]
            
        except SyntaxError as e:
            error_msg = f"Syntax error in HatchMCP wrapper '{hatch_wrapper}' at line {e.lineno}: {e.msg}"
            logger.error(error_msg)
            return False, [error_msg]
        except FileNotFoundError:
            error_msg = f"HatchMCP wrapper file '{hatch_wrapper}' not found"
            logger.error(error_msg)
            return False, [error_msg]
        except Exception as e:
            error_msg = f"Error validating import relationship: {str(e)}"
            logger.error(error_msg)
            return False, [error_msg]
