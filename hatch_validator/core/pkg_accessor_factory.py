"""Factory for creating package accessor chains.

This module provides the package accessor factory responsible for creating the appropriate
accessor chain based on the target schema version.
"""

from typing import Optional, List, Dict, Type
import logging

from hatch_validator.core.pkg_accessor_base import HatchPkgAccessor

logger = logging.getLogger("hatch.pkg_accessor_factory")

class HatchPkgAccessorFactory:
    """Factory class for creating package accessor chains.
    
    This factory creates the appropriate accessor chain based on the target
    schema version, setting up the Chain of Responsibility pattern correctly.
    The factory maintains a registry of available accessors and constructs
    chains that enable proper delegation between versions.
    """
    # Registry of available accessor versions (newest to oldest)
    _accessor_registry: Dict[str, Type[HatchPkgAccessor]] = {}
    _version_order: List[str] = []

    @classmethod
    def register_accessor(cls, version: str, accessor_class: Type[HatchPkgAccessor]) -> None:
        """Register an accessor class for a specific schema version.
        
        Args:
            version (str): Schema version (e.g., "1.1.0", "1.2.0")
            accessor_class (Type[HatchPkgAccessor]): Accessor class for the version
        """
        cls._accessor_registry[version] = accessor_class
        if version not in cls._version_order:
            cls._version_order.append(version)
            # Sort versions in descending order (newest first)
            cls._version_order.sort(reverse=True)
        logger.debug(f"Registered accessor for version {version}")

    @classmethod
    def get_supported_versions(cls) -> List[str]:
        """Get list of supported schema versions.
        
        Returns:
            List[str]: List of supported versions ordered newest to oldest
        """
        cls._ensure_accessors_loaded()
        return cls._version_order.copy()

    @classmethod
    def _ensure_accessors_loaded(cls) -> None:
        """Ensure all available accessors are loaded and registered."""
        if not cls._accessor_registry:
            # Import and register available accessors
            try:
                from hatch_validator.package.v1_1_0.accessor import HatchPkgAccessor as V110HatchPkgAccessor
                cls.register_accessor("1.1.0", V110HatchPkgAccessor)
            except ImportError as e:
                logger.warning(f"Could not load v1.1.0 accessor: {e}")
            try:
                from hatch_validator.package.v1_2_0.accessor import HatchPkgAccessor as V120HatchPkgAccessor
                cls.register_accessor("1.2.0", V120HatchPkgAccessor)
            except ImportError as e:
                logger.warning(f"Could not load v1.2.0 accessor: {e}")

            try:
                from hatch_validator.package.v1_2_1.accessor import HatchPkgAccessor as V121HatchPkgAccessor
                cls.register_accessor("1.2.1", V121HatchPkgAccessor)
            except ImportError as e:
                logger.warning(f"Could not load v1.2.1 accessor: {e}")

            try:
                from hatch_validator.package.v1_2_2.accessor import HatchPkgAccessor as V122HatchPkgAccessor
                cls.register_accessor("1.2.2", V122HatchPkgAccessor)
            except ImportError as e:
                logger.warning(f"Could not load v1.2.2 accessor: {e}")

    @classmethod
    def create_accessor_chain(cls, target_version: Optional[str] = None) -> HatchPkgAccessor:
        """Create appropriate accessor chain based on target version.
        
        Creates a chain of accessors ordered from newest to oldest schema versions.
        Each accessor in the chain can handle its specific version and delegate
        to older versions for unchanged access concerns.
        
        Args:
            target_version (str, optional): Specific schema version to target. 
                If None, uses the latest available version. Defaults to None.
        
        Returns:
            HatchPkgAccessor: Head of the accessor chain
        
        Raises:
            ValueError: If the target version is not supported or no accessors are available
        """
        cls._ensure_accessors_loaded()
        if not cls._accessor_registry:
            raise ValueError("No accessors available")
        # Determine target version
        if target_version is None:
            target_version = cls._version_order[0]  # Latest version

        elif target_version not in cls._accessor_registry:
            raise ValueError(f"Unsupported schema version: {target_version}. "
                             f"Supported versions: {cls._version_order}")
        logger.info(f"Creating accessor chain for target version: {target_version}")

        # Create chain starting from target version down to oldest
        target_index = cls._version_order.index(target_version)
        chain_versions = cls._version_order[target_index:]

        # Create accessors in order (newest to oldest)
        accessors = []
        for version in chain_versions:
            accessor_class = cls._accessor_registry[version]
            accessor = accessor_class()
            accessors.append(accessor)
            logger.debug(f"Created accessor for version {version}")

        # Link accessors (each points to the next older one)
        for i in range(len(accessors) - 1):
            accessors[i].set_next(accessors[i + 1])
            logger.debug(f"Linked accessor {chain_versions[i]} -> {chain_versions[i+1]}")

        head_accessor = accessors[0]
        logger.info(f"Accessor chain created successfully, head: {target_version}")
        return head_accessor
