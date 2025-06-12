"""Schema validation framework using Chain of Responsibility and Strategy patterns.

This module provides the abstract base classes and interfaces for the validation
framework, enabling extensible schema validation across different versions.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional
from pathlib import Path


class ValidationContext:
    """Context object that carries validation state through the validator chain.
    
    This context provides a consistent interface for passing validation resources
    and state between validators and strategies in the chain.
    """
    
    def __init__(self, package_dir: Optional[Path] = None, registry_data: Optional[Dict] = None,
                 allow_local_dependencies: bool = True, force_schema_update: bool = False):
        """Initialize validation context.
        
        Args:
            package_dir (Path, optional): Path to the package being validated. Defaults to None.
            registry_data (Dict, optional): Registry data for dependency validation. Defaults to None.
            allow_local_dependencies (bool, optional): Whether local dependencies are allowed. Defaults to True.
            force_schema_update (bool, optional): Whether to force schema updates. Defaults to False.
        """
        self.package_dir = package_dir
        self.registry_data = registry_data
        self.allow_local_dependencies = allow_local_dependencies
        self.force_schema_update = force_schema_update
        self.additional_data = {}
    
    def set_data(self, key: str, value: Any) -> None:
        """Set additional data in the context.
        
        Args:
            key (str): Key for the data
            value (Any): Value to store
        """
        self.additional_data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get additional data from the context.
        
        Args:
            key (str): Key for the data
            default (Any, optional): Default value if key not found. Defaults to None.
            
        Returns:
            Any: Value associated with the key or default
        """
        return self.additional_data.get(key, default)


class SchemaValidator(ABC):
    """Abstract base class for schema validators in the Chain of Responsibility pattern.
    
    Each validator in the chain can either handle the validation for a specific schema
    version or pass the request to the next validator in the chain.
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


class ValidatorFactory:
    """Factory class for creating schema validator chains.
    
    This factory creates the appropriate validator chain based on the target
    schema version, setting up the Chain of Responsibility pattern correctly.
    """
    
    @staticmethod
    def create_validator_chain(target_version: Optional[str] = None) -> SchemaValidator:
        """Create appropriate validator chain based on target version.
        
        Creates a chain of validators ordered from newest to oldest schema versions.
        If a specific version is requested, the chain will start with that version's
        validator.
        
        Args:
            target_version (str, optional): Specific schema version to target. Defaults to None.
            
        Returns:
            SchemaValidator: Head of the validator chain
            
        Raises:
            ValueError: If the target version is not supported
        """
        # Import here to avoid circular imports
        from .schema_validators_v1_1_0 import SchemaV1_1_0Validator
        
        # Create validators (newest to oldest when we have more versions)
        v1_1_0_validator = SchemaV1_1_0Validator()
        
        # If specific version requested, return that validator
        if target_version == "1.1.0":
            return v1_1_0_validator
        elif target_version is None:
            # Default to v1.1.0 for now (will be latest when we add more versions)
            return v1_1_0_validator
        else:
            raise ValueError(f"Unsupported schema version: {target_version}")
