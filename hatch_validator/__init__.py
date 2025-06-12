"""
Hatch-Validator package for validating Hatch packages and dependencies.

This package provides tools for validating Hatch packages, their metadata, and dependencies.
"""

__version__ = "0.3.2"

from .package_validator import HatchPackageValidator, PackageValidationError
from .dependency_resolver import DependencyResolver, DependencyResolutionError
from .schema_fetcher import SchemaFetcher
from .schema_cache import SchemaCache

from .schemas_retriever import (
    SchemaRetriever,
    get_package_schema, 
    get_registry_schema
)

__all__ = [
    'HatchPackageValidator',
    'PackageValidationError',
    'DependencyResolver', 
    'DependencyResolutionError',
    'SchemaRetriever',
    'SchemaFetcher',
    'SchemaCache',
    'get_package_schema',
    'get_registry_schema',
]