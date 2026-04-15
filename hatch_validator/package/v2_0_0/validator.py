"""Schema validation strategies and validator for v2.0.0.

This module provides concrete implementations of the validation strategies
and validator for schema version 2.0.0, following the Chain of Responsibility
and Strategy patterns.
"""

import logging
from typing import Dict, List, Tuple

from hatch_validator.core.validator_base import Validator as ValidatorBase
from hatch_validator.core.validation_context import ValidationContext

from .dependency_validation import DependencyValidation
from .schema_validation import SchemaValidation
from .provenance_validation import ProvenanceValidation
from .citations_validation import CitationsValidation


# Configure logging
logger = logging.getLogger("hatch.schema.v2_0_0.validator")
logger.setLevel(logging.INFO)


class Validator(ValidatorBase):
    """Validator for packages using schema version 2.0.0.
    
    Schema version 2.0.0 renames some fields (package_schema_version → hatch_schema_version,
    author → authors, tools[].description → tools[].desc), sets Docker dependencies to require
    tag, digest now instead of version_constraint, and makes version_constraint optional for
    all dependency types. This validator handles the new dependency structure and delegates
    unchanged validation logic to the previous validator in the chain.
    """
    
    def __init__(self, next_validator=None):
        """Initialize the v2.0.0 validator with strategies.
        
        Args:
            next_validator (Validator, optional): Next validator in chain. Defaults to None.
        """
        super().__init__(next_validator)
        self.schema_strategy = SchemaValidation()
        self.dependency_strategy = DependencyValidation()
        self.provenance_strategy = ProvenanceValidation()
        self.citations_strategy = CitationsValidation()
    
    def can_handle(self, schema_version: str) -> bool:
        """Determine if this validator can handle the given schema version.
        
        Args:
            schema_version (str): Schema version to check
            
        Returns:
            bool: True if this validator can handle the schema version
        """
        return schema_version == "2.0.0"
    
    def validate(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validation entry point for packages following schema v2.0.0.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources and state
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether validation was successful
                - List[str]: List of validation errors
        """
        # Support new field name for v2.0.0 with fallback for legacy packages.
        schema_version = metadata.get("hatch_schema_version") or metadata.get("package_schema_version", "")
        
        # Check if we can handle this version
        if not self.can_handle(schema_version):
            if self.next_validator:
                return self.next_validator.validate(metadata, context)
            return False, [f"Unsupported schema version: {schema_version}"]
        
        logger.info(f"Validating package metadata using v2.0.0 validator")
        
        all_errors = []
        is_valid = True
        
        # 1. Validate against JSON schema
        schema_valid, schema_errors = self.validate_schema(metadata, context)
        if not schema_valid:
            all_errors.extend(schema_errors)
            is_valid = False
            # If schema validation fails, don't continue with other validations
            return is_valid, all_errors
        
        # 2. Validate Hatch/Python/System dependencies — unchanged from v1.2.2, delegated via chain
        deps_valid, deps_errors = self.validate_dependencies(metadata, context)
        if not deps_valid:
            all_errors.extend(deps_errors)
            is_valid = False

        # 3. Validate Docker dependencies — new concern owned by v2.0.0
        docker_valid, docker_errors = self.validate_docker_dependencies(metadata, context)
        if not docker_valid:
            all_errors.extend(docker_errors)
            is_valid = False

        # 5. Validate provenance metadata
        provenance_valid, provenance_errors = self.validate_provenance(metadata, context)
        if not provenance_valid:
            all_errors.extend(provenance_errors)
            is_valid = False

        # 6. Validate citations metadata
        citations_valid, citations_errors = self.validate_citations(metadata, context)
        if not citations_valid:
            all_errors.extend(citations_errors)
            is_valid = False

        # 7. Validate entry point and tools if package directory is available
        if context.package_dir:
            entry_valid, entry_errors = self.validate_entry_point(metadata, context)
            if not entry_valid:
                all_errors.extend(entry_errors)
                is_valid = False

            if entry_valid:
                tools_valid, tools_errors = self.validate_tools(metadata, context)
                if not tools_valid:
                    all_errors.extend(tools_errors)
                    is_valid = False
        
        return is_valid, all_errors
    
    def validate_schema(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata against schema for v2.0.0.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        logger.debug("Validating package metadata against v2.0.0 schema")
        return self.schema_strategy.validate_schema(metadata, context)
    
    def validate_docker_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate Docker dependencies for v2.0.0.

        Docker dependencies are new in v2.0.0 (digest-based, no version_constraint).
        This is a new concern owned entirely by v2.0.0, analogous to validate_provenance
        and validate_citations.

        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources

        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        logger.debug("Validating Docker dependencies for v2.0.0")
        return self.dependency_strategy.validate_dependencies(metadata, context)

    def validate_provenance(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate provenance metadata for v2.0.0."""
        return self.provenance_strategy.validate_provenance(metadata, context)

    def validate_citations(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate citations metadata for v2.0.0."""
        return self.citations_strategy.validate_citations(metadata, context)

    def validate_tools(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate tools for v2.0.0.

        Tools validation (declared tool names must match @mcp.tool()-decorated functions)
        is unchanged from v1.2.1, so delegate to the next validator in the chain.

        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources

        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        logger.debug("Delegating tools validation to v1.2.1 via chain")
        if self.next_validator:
            return self.next_validator.validate_tools(metadata, context)
        return False, ["No validator available for tools validation"]

    def validate_entry_point(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate entry point for v2.0.0.

        Entry point validation (dual mcp_server + hatch_mcp_server file checks)
        is unchanged from v1.2.1, so delegate to the next validator in the chain.

        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources

        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        logger.debug("Delegating entry point validation to v1.2.1 via chain")
        if self.next_validator:
            return self.next_validator.validate_entry_point(metadata, context)
        return False, ["No validator available for entry point validation"]
