"""Strategy interfaces for validation components.

This module provides the strategy interfaces used by validators to implement
version-specific validation logic.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple

from .validation_context import ValidationContext


class ValidationStrategy(ABC):
    """Base interface for all validation strategies.
    
    This serves as a marker interface for validation strategies and provides
    common functionality that all strategies might need.
    """
    pass


class DependencyValidationStrategy(ValidationStrategy):
    """Strategy interface for validating package dependencies.
    
    Different schema versions may have different dependency structures,
    so this strategy allows for version-specific dependency validation logic.
    """
    
    @abstractmethod
    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate dependencies according to specific schema version.
        
        Args:
            metadata (Dict): Package metadata containing dependency information
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether dependency validation was successful
                - List[str]: List of dependency validation errors
        """
        pass


class ToolsValidationStrategy(ValidationStrategy):
    """Strategy interface for validating tool declarations.
    
    Validates that tools declared in metadata actually exist in the entry point file
    and are properly accessible.
    """
    
    @abstractmethod
    def validate_tools(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate tools according to specific schema version.
        
        Args:
            metadata (Dict): Package metadata containing tool declarations
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether tool validation was successful
                - List[str]: List of tool validation errors
        """
        pass


class EntryPointValidationStrategy(ValidationStrategy):
    """Strategy interface for validating entry point files.
    
    Validates that the entry point specified in metadata exists and is accessible.
    """
    
    @abstractmethod
    def validate_entry_point(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate entry point according to specific schema version.
        
        Args:
            metadata (Dict): Package metadata containing entry point information
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether entry point validation was successful
                - List[str]: List of entry point validation errors
        """
        pass


class SchemaValidationStrategy(ValidationStrategy):
    """Strategy interface for validating metadata against JSON schema.
    
    Validates that the package metadata conforms to the JSON schema for
    the specific schema version.
    """
    
    @abstractmethod
    def validate_schema(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata against JSON schema for specific version.
        
        Args:
            metadata (Dict): Package metadata to validate against schema
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether schema validation was successful
                - List[str]: List of schema validation errors
        """
        pass
