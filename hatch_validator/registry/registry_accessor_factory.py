"""Factory for creating registry accessor chains.

This module provides the factory responsible for creating the appropriate
registry accessor chain based on the target schema version.
"""

from typing import Optional, List, Dict, Type
import logging

from .registry_accessor_base import RegistryAccessorBase

logger = logging.getLogger("hatch.registry_accessor_factory")


class RegistryAccessorFactory:
    """Factory class for creating registry accessor chains.
    
    This factory creates the appropriate registry accessor chain based on the target
    schema version, setting up the Chain of Responsibility pattern correctly.
    The factory maintains a registry of available accessors and constructs
    chains that enable proper delegation between versions.
    """
    
    # Registry of available accessor versions (newest to oldest)
    _accessor_registry: Dict[str, Type[RegistryAccessorBase]] = {}
    _version_order: List[str] = []
    
    @classmethod
    def register_accessor(cls, version: str, accessor_class: Type[RegistryAccessorBase]) -> None:
        """Register a registry accessor for a specific schema version.
        
        Args:
            version (str): Schema version string (e.g., '1.1.0').
            accessor_class (Type[RegistryAccessorBase]): Accessor class to register.
        """
        cls._accessor_registry[version] = accessor_class
        
        # Maintain version order (newest first)
        if version not in cls._version_order:
            cls._version_order.append(version)
            cls._version_order.sort(reverse=True)  # Newest first
        
        logger.debug(f"Registered registry accessor for version {version}")
    
    @classmethod
    def get_supported_versions(cls) -> List[str]:
        """Get list of supported schema versions.
        
        Returns:
            List[str]: List of supported version strings, ordered newest to oldest.
        """
        cls._ensure_accessors_loaded()
        return cls._version_order.copy()
    @classmethod
    def _ensure_accessors_loaded(cls) -> None:
        """Ensure all available accessors are loaded and registered."""
        if not cls._accessor_registry:
            # Import and register v1.2.0 accessor (newest first)
            # from hatch_validator.registry.v1_2_0.registry_accessor import RegistryAccessor as V120RegistryAccessor
            # cls.register_accessor('1.2.0', V120RegistryAccessor)
            
            # Import and register v1.1.0 accessor
            from hatch_validator.registry.v1_1_0.registry_accessor import RegistryAccessor as V110RegistryAccessor
            cls.register_accessor('1.1.0', V110RegistryAccessor)
    
    @classmethod
    def create_accessor_chain(cls, target_version: Optional[str] = None) -> RegistryAccessorBase:
        """Create a registry accessor chain for handling schema versions.
        
        The chain is built starting from the target version (or newest available)
        and includes all older versions as fallbacks in the chain.
        
        Args:
            target_version (str, optional): Target schema version. If None, uses newest.
            
        Returns:
            RegistryAccessorBase: Root accessor of the chain.
            
        Raises:
            ValueError: If target_version is specified but not supported.
        """
        cls._ensure_accessors_loaded()
        
        if not cls._accessor_registry:
            raise ValueError("No registry accessors available")
        
        # Determine starting version
        if target_version:
            if target_version not in cls._accessor_registry:
                raise ValueError(f"Unsupported schema version: {target_version}")
            start_index = cls._version_order.index(target_version)
        else:
            start_index = 0  # Start with newest
        
        # Build chain from target version to oldest
        chain_versions = cls._version_order[start_index:]
        
        if not chain_versions:
            raise ValueError("No versions available for chain creation")
        
        # Create accessors in reverse order (oldest first)
        chain_accessors = []
        for version in reversed(chain_versions):
            accessor_class = cls._accessor_registry[version]
            chain_accessors.append(accessor_class())
        
        # Link the chain (each accessor points to the next older one)
        for i in range(len(chain_accessors) - 1):
            chain_accessors[i]._successor = chain_accessors[i + 1]
        
        # Return the newest accessor (first in the chain)
        root_accessor = chain_accessors[0]
        
        logger.debug(f"Created registry accessor chain with {len(chain_accessors)} versions")
        return root_accessor
    
    @classmethod
    def create_accessor_for_data(cls, registry_data: Dict) -> Optional[RegistryAccessorBase]:
        """Create an accessor that can handle the given registry data.
        
        Args:
            registry_data (Dict): Registry data to find an accessor for.
            
        Returns:
            Optional[RegistryAccessorBase]: Accessor that can handle the data, or None.
        """
        chain = cls.create_accessor_chain()
        return chain.handle_request(registry_data)
