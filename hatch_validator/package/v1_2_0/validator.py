"""Schema validation strategies and validator for v1.2.0.

This module provides concrete implementations of the validation strategies
and validator for schema version 1.2.0, following the Chain of Responsibility
and Strategy patterns.
"""

import logging
from typing import Dict, List, Tuple

from hatch_validator.core.validator_base import Validator as ValidatorBase
from hatch_validator.core.validation_context import ValidationContext

from .dependency_validation import DependencyValidation
from .schema_validation import SchemaValidation


# Configure logging
logger = logging.getLogger("hatch.schema.v1_2_0.validator")
logger.setLevel(logging.INFO)


class Validator(ValidatorBase):
    """Validator for packages using schema version 1.2.0.
    
    Schema version 1.2.0 introduces a unified dependencies structure
    with support for hatch, python, system, and docker dependencies.
    This validator handles the new dependency structure and delegates
    unchanged validation logic (entry point, tools) to the previous validator in the chain.
    """
    
    def __init__(self, next_validator=None):
        """Initialize the v1.2.0 validator with strategies.
        
        Args:
            next_validator (Validator, optional): Next validator in chain. Defaults to None.
        """
        super().__init__(next_validator)
        self.schema_strategy = SchemaValidation()
        self.dependency_strategy = DependencyValidation()
    
    def can_handle(self, schema_version: str) -> bool:
        """Determine if this validator can handle the given schema version.
        
        Args:
            schema_version (str): Schema version to check
            
        Returns:
            bool: True if this validator can handle the schema version
        """
        return schema_version == "1.2.0"
    
    def validate(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validation entry point for packages following schema v1.2.0.
        
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
        
        logger.info(f"Validating package metadata using v1.2.0 validator")
        
        all_errors = []
        is_valid = True
        
        # 1. Validate against JSON schema
        schema_valid, schema_errors = self.validate_schema(metadata, context)
        if not schema_valid:
            all_errors.extend(schema_errors)
            is_valid = False
            # If schema validation fails, don't continue with other validations
            return is_valid, all_errors
        
        # 2. Validate dependencies (major change in v1.2.0)
        deps_valid, deps_errors = self.validate_dependencies(metadata, context)
        if not deps_valid:
            all_errors.extend(deps_errors)
            is_valid = False
        
        # 3. Validate entry point (if package directory is provided)
        if context.package_dir:
            entry_valid, entry_errors = self.validate_entry_point(metadata, context)
            if not entry_valid:
                all_errors.extend(entry_errors)
                is_valid = False
            
            # 4. Validate tools (if entry point validation passed)
            if entry_valid:
                tools_valid, tools_errors = self.validate_tools(metadata, context)
                if not tools_valid:
                    all_errors.extend(tools_errors)
                    is_valid = False
        
        return is_valid, all_errors
    
    def validate_schema(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata against schema for v1.2.0.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        logger.debug("Validating package metadata against v1.2.0 schema")
        return self.schema_strategy.validate_schema(metadata, context)
    
    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate dependencies for v1.2.0.
        
        This method implements the new unified dependencies structure
        introduced in v1.2.0.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        logger.debug("Validating package dependencies for v1.2.0")
        return self.dependency_strategy.validate_dependencies(metadata, context)
