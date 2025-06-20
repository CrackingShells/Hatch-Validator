"""Schema validation strategies and validator for v1.1.0.

This module provides concrete implementations of the validation strategies
and validator for schema version 1.1.0, following the Chain of Responsibility
and Strategy patterns.
"""

import logging
from typing import Dict, List, Tuple

from hatch_validator.core.validator_base import Validator as ValidatorBase
from hatch_validator.core.validation_context import ValidationContext

from .dependency_validation import DependencyValidation
from .schema_validation import SchemaValidation
from .entry_point_validation import EntryPointValidation
from .tools_validation import ToolsValidation


# Configure logging
logger = logging.getLogger("hatch.schema.v1_1_0.validator")
logger.setLevel(logging.DEBUG)

class Validator(ValidatorBase):
    """Validator for packages using schema version 1.1.0
    
    Schema version 1.1.0 includes hatch_dependencies and python_dependencies
    as separate arrays.
    As the end of the validator chain, this implementation provides concrete
    implementations for all validation methods.
    
    Note:
        This validator is the first to be implemented since the introduction
        of the chain of responsibility pattern, so it is the last in the chain.
    """
    def __init__(self, next_validator=None):
        """Initialize the v1.1.0 validator with strategies.
        
        Args:
            next_validator (Validator, optional): Next validator in chain. Defaults to None.
        """
        super().__init__(next_validator)
        self.schema_strategy = SchemaValidation()
        self.dependency_strategy = DependencyValidation()
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
        """Validation entry point for packages following schema v1.1.0.
        
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
        schema_valid, schema_errors = self.validate_schema(metadata, context)
        if not schema_valid:
            all_errors.extend(schema_errors)
            is_valid = False
            # If schema validation fails, don't continue with other validations
            return is_valid, all_errors
        
        # 2. Validate dependencies
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
        """Validate metadata against schema for v1.1.0.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        logger.debug("Validating schema for v1.1.0")
        return self.schema_strategy.validate_schema(metadata, context)
        
    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate dependencies for v1.1.0.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        logger.debug("Validating dependencies for v1.1.0")
        return self.dependency_strategy.validate_dependencies(metadata, context)
        
    def validate_entry_point(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate entry point for v1.1.0.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        logger.debug("Validating entry point for v1.1.0")
        return self.entry_point_strategy.validate_entry_point(metadata, context)
        
    def validate_tools(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate tools for v1.1.0.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        logger.debug("Validating tools for v1.1.0")
        return self.tools_strategy.validate_tools(metadata, context)
