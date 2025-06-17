"""Base validator class for Chain of Responsibility pattern.

This module provides the abstract base class for schema validators that
implement the Chain of Responsibility pattern.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional

from .validation_context import ValidationContext


class SchemaValidator(ABC):
    """Abstract base class for schema validators in the Chain of Responsibility pattern.
    
    Each validator in the chain can either handle the validation for a specific schema
    version or pass the request to the next validator in the chain. The base class
    provides default delegation methods for each specific validation concern,
    allowing concrete validators to override only the validation concerns that
    have changed in their version.
    """
    
    def __init__(self, next_validator: Optional['SchemaValidator'] = None):
        """Initialize the validator with an optional next validator in the chain.
        
        Args:
            next_validator (SchemaValidator, optional): Next validator in the chain. Defaults to None.
        """
        self.next_validator = next_validator
    
    @abstractmethod
    def validate(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata or delegate to next validator in chain.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources and state
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether validation was successful
                - List[str]: List of validation errors
        """
        pass
    
    @abstractmethod
    def can_handle(self, schema_version: str) -> bool:
        """Determine if this validator can handle the given schema version.
        
        Args:
            schema_version (str): Schema version to check
            
        Returns:
            bool: True if this validator can handle the schema version
        """
        pass
    
    def set_next(self, validator: 'SchemaValidator') -> 'SchemaValidator':
        """Set the next validator in the chain.
        
        Args:
            validator (SchemaValidator): Next validator to set
            
        Returns:
            SchemaValidator: The validator that was set as next
        """
        self.next_validator = validator
        return validator
    
    def validate_schema(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata against schema.
        
        Default behavior: delegate to next validator in chain if available.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
            
        Raises:
            NotImplementedError: If there is no next validator and this method is not overridden
        """
        if self.next_validator:
            return self.next_validator.validate_schema(metadata, context)
        raise NotImplementedError("Schema validation not implemented for this validator")
    
    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate package dependencies.
        
        Default behavior: delegate to next validator in chain if available.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
            
        Raises:
            NotImplementedError: If there is no next validator and this method is not overridden
        """
        if self.next_validator:
            return self.next_validator.validate_dependencies(metadata, context)
        raise NotImplementedError("Dependency validation not implemented for this validator")
    
    def validate_entry_point(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate package entry point.
        
        Default behavior: delegate to next validator in chain if available.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
            
        Raises:
            NotImplementedError: If there is no next validator and this method is not overridden
        """
        if self.next_validator:
            return self.next_validator.validate_entry_point(metadata, context)
        raise NotImplementedError("Entry point validation not implemented for this validator")
    
    def validate_tools(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate package tools.
        
        Default behavior: delegate to next validator in chain if available.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
            
        Raises:
            NotImplementedError: If there is no next validator and this method is not overridden
        """
        if self.next_validator:
            return self.next_validator.validate_tools(metadata, context)
        raise NotImplementedError("Tools validation not implemented for this validator")
