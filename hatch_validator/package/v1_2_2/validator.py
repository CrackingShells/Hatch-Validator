"""Schema validation strategies and validator for v1.2.2.

This module provides concrete implementations of the validation strategies
and validator for schema version 1.2.2, following the Chain of Responsibility
and Strategy patterns.

Schema version 1.2.2 introduces conda package manager support for Python
dependencies while maintaining dual entry point support from v1.2.1.
"""

import logging
from typing import Dict, List, Tuple

from hatch_validator.core.validator_base import Validator as ValidatorBase
from hatch_validator.core.validation_context import ValidationContext

from .schema_validation import SchemaValidation
from .dependency_validation import DependencyValidation


# Configure logging
logger = logging.getLogger("hatch.schema.v1_2_2.validator")
logger.setLevel(logging.INFO)


class Validator(ValidatorBase):
    """Validator for packages using schema version 1.2.2.
    
    Schema version 1.2.2 introduces conda package manager support for Python
    dependencies. This validator implements enhanced dependency validation while
    delegating unchanged validation logic (entry points, tools) to the v1.2.1 validator.
    """
    
    def __init__(self, next_validator=None):
        """Initialize the v1.2.2 validator with strategies.
        
        Args:
            next_validator (Validator, optional): Next validator in chain. Defaults to None.
        """
        super().__init__(next_validator)
        self.schema_strategy = SchemaValidation()
        self.dependency_strategy = DependencyValidation()
    
    def can_handle(self, schema_version: str) -> bool:
        """Check if this validator can handle the given schema version.
        
        Args:
            schema_version (str): Schema version to check
            
        Returns:
            bool: True if this validator can handle the version, False otherwise
        """
        return schema_version == "1.2.2"
    
    def validate(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validation entry point for packages following schema v1.2.2.
        
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
        
        logger.info(f"Validating package metadata using v1.2.2 validator")
        
        all_errors = []
        is_valid = True
        
        # 1. Validate against JSON schema
        schema_valid, schema_errors = self.validate_schema(metadata, context)
        if not schema_valid:
            all_errors.extend(schema_errors)
            is_valid = False
            # If schema validation fails, don't continue with other validations
            return is_valid, all_errors
        
        # 2. Validate dependencies (enhanced with conda support)
        deps_valid, deps_errors = self.validate_dependencies(metadata, context)
        if not deps_valid:
            all_errors.extend(deps_errors)
            is_valid = False
        
        # 3. Validate entry point (delegate to v1.2.1 - unchanged)
        entry_point_valid, entry_point_errors = self.validate_entry_point(metadata, context)
        if not entry_point_valid:
            all_errors.extend(entry_point_errors)
            is_valid = False
        
        # 4. Validate tools (delegate to v1.2.1 - unchanged)
        tools_valid, tools_errors = self.validate_tools(metadata, context)
        if not tools_valid:
            all_errors.extend(tools_errors)
            is_valid = False
        
        if is_valid:
            logger.info("Package metadata validation successful for v1.2.2")
        else:
            logger.warning(f"Package metadata validation failed for v1.2.2: {len(all_errors)} errors")
        
        return is_valid, all_errors
    
    def validate_schema(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata against schema for v1.2.2.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        logger.debug("Validating package metadata against v1.2.2 schema")
        return self.schema_strategy.validate_schema(metadata, context)
    
    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate dependencies for v1.2.2.
        
        Dependencies structure includes conda support for Python packages.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        logger.debug("Validating dependencies with conda support for v1.2.2")
        return self.dependency_strategy.validate_dependencies(metadata, context)
    
    def validate_entry_point(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate dual entry point for v1.2.2.
        
        Entry point validation is unchanged from v1.2.1, so delegate to the next validator.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
        
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        logger.debug("Delegating entry point validation to v1.2.1 validator")
        if self.next_validator:
            return self.next_validator.validate_entry_point(metadata, context)
        return False, ["No validator available for entry point validation"]
    
    def validate_tools(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate tools with FastMCP server enforcement for v1.2.2.
        
        Tools validation is unchanged from v1.2.1, so delegate to the next validator.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
        
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        logger.debug("Delegating tools validation to v1.2.1 validator")
        if self.next_validator:
            return self.next_validator.validate_tools(metadata, context)
        return False, ["No validator available for tools validation"]

