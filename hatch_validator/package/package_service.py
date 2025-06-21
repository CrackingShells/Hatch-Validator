"""Package service for package metadata operations.

Provides a high-level interface for working with package metadata, including
version-aware access to all top-level fields and dependencies.
"""

import logging
from typing import Optional, Dict, Any, List

from hatch_validator.core.pkg_accessor_factory import HatchPkgAccessorFactory
from hatch_validator.core.pkg_accessor_base import HatchPkgAccessor

logger = logging.getLogger("hatch.package_service")

class PackageService:
    """Service for package metadata operations.

    Provides a high-level interface for working with package metadata,
    including version-aware access to all top-level fields and dependencies.
    This service uses the accessor chain pattern to handle different
    package schema versions automatically.
    """
    def __init__(self, metadata: Optional[Dict[str, Any]] = None):
        """Initialize the package service.

        Args:
            metadata (Dict[str, Any], optional): Initial package metadata.
        """
        self._metadata: Optional[Dict[str, Any]] = metadata
        self._accessor: Optional[HatchPkgAccessor] = None
        if metadata:
            self.load_metadata(metadata)

    def load_metadata(self, metadata: Dict[str, Any]) -> None:
        """Load package metadata and initialize appropriate accessor.

        Args:
            metadata (Dict[str, Any]): Package metadata to load.

        Raises:
            ValueError: If no accessor can handle the package metadata.
        """
        self._metadata = metadata
        schema_version = metadata.get("package_schema_version")

        if not schema_version:
            raise ValueError("Missing 'package_schema_version' in metadata.")
        
        self._accessor = HatchPkgAccessorFactory.create_accessor_chain(schema_version)
        if not self._accessor:
            raise ValueError(f"No accessor found for schema version: {schema_version}")
        
        logger.debug(f"Loaded package metadata with schema version: {schema_version}")

    def is_loaded(self) -> bool:
        """Check if package metadata is loaded.

        Returns:
            bool: True if package metadata is loaded and accessible.
        """
        return self._metadata is not None and self._accessor is not None

    def get_field(self, field: str) -> Any:
        """Get a top-level field from the package metadata.

        Args:
            field (str): Field name to retrieve.

        Returns:
            Any: Value of the field, or None if not found.

        Raises:
            ValueError: If metadata is not loaded or accessor is not available.
        """
        if not self.is_loaded():
            raise ValueError("Package metadata is not loaded.")
        if not hasattr(self._accessor, f"get_{field}"):
            raise AttributeError(f"Accessor does not support field: {field}")
        return getattr(self._accessor, f"get_{field}")(self._metadata)

    def get_dependencies(self) -> Dict[str, Any]:
        """Get all dependencies from the package metadata.

        Returns:
            Dict[str, Any]: Dictionary of dependencies by type.

        Raises:
            ValueError: If metadata is not loaded.
        """
        if not self.is_loaded():
            raise ValueError("Package metadata is not loaded.")
        return self._accessor.get_dependencies(self._metadata)
    
    def is_local_dependency(self, dep: Dict[str, Any]) -> bool:
        """Check if a dependency is local.

        Args:
            dep (Dict[str, Any]): Dependency dictionary.

        Returns:
            bool: True if the dependency is local, False otherwise.

        Raises:
            ValueError: If metadata is not loaded.
        """
        if not self.is_loaded():
            raise ValueError("Package metadata is not loaded.")
        return self._accessor.is_local_dependency(dep)

    def get_entry_point(self) -> Any:
        """Get the entry point from the package metadata.

        Returns:
            Any: Entry point value.

        Raises:
            ValueError: If metadata is not loaded.
        """
        if not self.is_loaded():
            raise ValueError("Package metadata is not loaded.")
        return self._accessor.get_entry_point(self._metadata)

    def get_tools(self) -> Any:
        """Get the tools from the package metadata.

        Returns:
            Any: Tools value.

        Raises:
            ValueError: If metadata is not loaded.
        """
        if not self.is_loaded():
            raise ValueError("Package metadata is not loaded.")
        return self._accessor.get_tools(self._metadata)
