"""
Hatch-Validator package for validating Hatch packages and dependencies.

This package provides tools for validating Hatch packages, their metadata, and dependencies.
"""

__version__ = "0.3.1"

from .package_validator import HatchPackageValidator, PackageValidationError
from .dependency_resolver import DependencyResolver, DependencyResolutionError
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
    'get_package_schema',
    'get_registry_schema',
]