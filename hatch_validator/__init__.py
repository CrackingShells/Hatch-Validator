"""
Hatch-Validator package for validating Hatch packages and dependencies.

This package provides tools for validating Hatch packages, their metadata, and dependencies.
"""

__version__ = "0.6.3"

# Core validation framework
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.core.validator_base import Validator
from hatch_validator.core.validation_strategy import (
    ValidationStrategy,
    DependencyValidationStrategy,
    ToolsValidationStrategy,
    EntryPointValidationStrategy,
    SchemaValidationStrategy
)
from hatch_validator.core.validator_factory import ValidatorFactory

# Package validator
from hatch_validator.package_validator import HatchPackageValidator, PackageValidationError

# Schema handling components
from hatch_validator.schemas.schema_fetcher import SchemaFetcher
from hatch_validator.schemas.schema_cache import SchemaCache
from hatch_validator.schemas.schemas_retriever import (
    SchemaRetriever,
    get_package_schema, 
    get_registry_schema
)

# Registry Access
from hatch_validator.registry.registry_service import RegistryService
from hatch_validator.registry.v1_1_0.registry_accessor import RegistryAccessor as V110RegistryAccessor

# Version-specific implementations will be imported when needed via the factory

__all__ = [
    # Core validation framework
    'ValidationContext',
    'Validator',
    'ValidationStrategy',
    'DependencyValidationStrategy',
    'ToolsValidationStrategy',
    'EntryPointValidationStrategy',
    'SchemaValidationStrategy',
    'ValidatorFactory',
    
    # Package validator
    'HatchPackageValidator',
    'PackageValidationError',
    
    # Schema handling components
    'SchemaRetriever',
    'SchemaFetcher',
    'SchemaCache',
    'get_package_schema',
    'get_registry_schema',

    # Registry Access
    'RegistryService',
    'V110RegistryAccessor'
]