"""Schema validation strategies and validator for v1.1.0.

This module provides concrete implementations of the validation strategies
and validator for schema version 1.1.0, following the Chain of Responsibility
and Strategy patterns.
"""

import ast
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import jsonschema

from hatch_validator.core.validator_base import SchemaValidator
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.core.validation_strategy import (
    DependencyValidationStrategy,
    ToolsValidationStrategy,
    EntryPointValidationStrategy,
    SchemaValidationStrategy
)
from hatch_validator.schemas.schemas_retriever import get_package_schema
from .dependency_validation_strategy import DependencyValidationV1_1_0


# Configure logging
logger = logging.getLogger("hatch.schema_validators_v1_1_0")
logger.setLevel(logging.INFO)


class SchemaValidation(SchemaValidationStrategy):
    """Strategy for validating metadata against JSON schema for v1.1.0."""
    
    def validate_schema(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata against v1.1.0 schema.
        
        Args:
            metadata (Dict): Package metadata to validate against schema
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether schema validation was successful
                - List[str]: List of schema validation errors
        """
        try:
            # Load schema for v1.1.0
            schema = get_package_schema(version="1.1.0", force_update=context.force_schema_update)
            if not schema:
                error_msg = "Failed to load package schema version 1.1.0"
                logger.error(error_msg)
                return False, [error_msg]
            
            # Validate against schema
            jsonschema.validate(instance=metadata, schema=schema)
            return True, []
            
        except jsonschema.exceptions.ValidationError as e:
            return False, [f"Schema validation error: {e.message}"]
        except Exception as e:
            return False, [f"Error during schema validation: {str(e)}"]


class EntryPointValidation(EntryPointValidationStrategy):
    """Strategy for validating entry point files for v1.1.0."""
    
    def validate_entry_point(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate entry point according to v1.1.0 schema.
        
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
            return False, ["No entry_point specified in metadata"]
        
        if not context.package_dir:
            return False, ["Package directory not provided for entry point validation"]
        
        entry_path = context.package_dir / entry_point
        if not entry_path.exists():
            return False, [f"Entry point file '{entry_point}' does not exist"]
        
        if not entry_path.is_file():
            return False, [f"Entry point '{entry_point}' is not a file"]
        
        return True, []


class ToolsValidation(ToolsValidationStrategy):
    """Strategy for validating tool declarations for v1.1.0."""
    
    def validate_tools(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate tools according to v1.1.0 schema.
        
        Args:
            metadata (Dict): Package metadata containing tool declarations
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether tool validation was successful
                - List[str]: List of tool validation errors
        """
        tools = metadata.get('tools', [])
        if not tools:
            return True, []
        
        entry_point = metadata.get('entry_point')
        if not entry_point:
            return False, ["Entry point required for tool validation"]
        
        if not context.package_dir:
            return False, ["Package directory not provided for tool validation"]
        
        errors = []
        all_exist = True
        
        # Parse the entry point file to get function names
        try:
            module_path = context.package_dir / entry_point
            with open(module_path, 'r', encoding='utf-8') as file:
                try:
                    tree = ast.parse(file.read(), filename=str(module_path))
                    
                    # Get all function names defined in the file
                    function_names = [node.name for node in ast.walk(tree) 
                                    if isinstance(node, ast.FunctionDef)]
                    
                    logger.debug(f"Found functions in {entry_point}: {function_names}")
                    
                    # Check for each tool
                    for tool in tools:
                        tool_name = tool.get('name')
                        if not tool_name:
                            logger.error(f"Tool metadata missing name: {tool}")
                            errors.append("Tool missing name in metadata")
                            all_exist = False
                            continue
                        
                        # Check if the tool function is defined in the file
                        if tool_name not in function_names:
                            logger.error(f"Tool '{tool_name}' not found in entry point")
                            errors.append(f"Tool '{tool_name}' not found in entry point")
                            all_exist = False
                    
                except SyntaxError as e:
                    logger.error(f"Syntax error in {entry_point}: {e}")
                    return False, [f"Syntax error in {entry_point}: {e}"]
                    
        except Exception as e:
            logger.error(f"Error validating tools: {str(e)}")
            return False, [f"Error validating tools: {str(e)}"]
            
        return all_exist, errors


class SchemaValidator(SchemaValidator):
    """Validator for schema version 1.1.0.
    
    This validator handles validation for packages using schema version 1.1.0,
    which includes hatch_dependencies and python_dependencies as separate arrays.
    """
    def __init__(self, next_validator=None):
        """Initialize the v1.1.0 validator with strategies.
        
        Args:
            next_validator (SchemaValidator, optional): Next validator in chain. Defaults to None.
        """
        super().__init__(next_validator)
        self.schema_strategy = SchemaValidation()
        self.dependency_strategy = DependencyValidationV1_1_0()
        self.entry_point_strategy = EntryPointValidation()
        self.tools_strategy = ToolsValidation()
        
    def can_handle(self, schema_version: str) -> bool:
        """Determine if this validator can handle the given schema version.
        
        Args:
            schema_version (str): Schema version to check
            
        Returns:
            bool: True if this validator can handle the schema version
        """
        return schema_version == "1.1.0"
    
    def validate(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata against v1.1.0 schema.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources and state
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether validation was successful
                - List[str]: List of validation errors
        """
        schema_version = metadata.get("package_schema_version", "")
        
        # Check if we can handle this version
        if not self.can_handle(schema_version):
            if self.next_validator:
                return self.next_validator.validate(metadata, context)
            return False, [f"Unsupported schema version: {schema_version}"]
        
        logger.info(f"Validating package metadata using v1.1.0 validator")
        
        all_errors = []
        is_valid = True
        
        # 1. Validate against JSON schema
        schema_valid, schema_errors = self.schema_strategy.validate_schema(metadata, context)
        if not schema_valid:
            all_errors.extend(schema_errors)
            is_valid = False
            # If schema validation fails, don't continue with other validations
            return is_valid, all_errors
        
        # 2. Validate dependencies
        deps_valid, deps_errors = self.dependency_strategy.validate_dependencies(metadata, context)
        if not deps_valid:
            all_errors.extend(deps_errors)
            is_valid = False
        
        # 3. Validate entry point (if package directory is provided)
        if context.package_dir:
            entry_valid, entry_errors = self.entry_point_strategy.validate_entry_point(metadata, context)
            if not entry_valid:
                all_errors.extend(entry_errors)
                is_valid = False
            
            # 4. Validate tools (if entry point validation passed)
            if entry_valid:
                tools_valid, tools_errors = self.tools_strategy.validate_tools(metadata, context)
                if not tools_valid:
                    all_errors.extend(tools_errors)
                    is_valid = False
        
        return is_valid, all_errors
