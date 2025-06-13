"""Registry interaction utilities for package validation.

This module provides utilities for interacting with package registries,
loading registry data, and querying package information that are independent
of specific schema versions.
"""

import json
import os
from typing import Dict, List, Set, Tuple, Optional, Any
from pathlib import Path
from abc import ABC, abstractmethod


class RegistryError(Exception):
    """Exception raised for registry-related errors."""
    pass


class RegistryPackageInfo:
    """Information about a package from the registry.
    
    Contains metadata about a package including its name, available versions,
    dependencies, and other registry-specific information.
    """
    
    def __init__(self, name: str, versions: List[str], metadata: Dict[str, Any]):
        """Initialize package information.
        
        Args:
            name (str): Package name.
            versions (List[str]): List of available versions.
            metadata (Dict[str, Any]): Additional package metadata.
        """
        self.name = name
        self.versions = versions
        self.metadata = metadata
    
    def has_version(self, version: str) -> bool:
        """Check if a specific version is available.
        
        Args:
            version (str): Version string to check.
            
        Returns:
            bool: True if version is available.
        """
        return version in self.versions
    
    def get_latest_version(self) -> Optional[str]:
        """Get the latest available version.
        
        Returns:
            Optional[str]: Latest version string, or None if no versions available.
        """
        if not self.versions:
            return None
        # Simple string sorting - could be improved with proper version sorting
        return sorted(self.versions, reverse=True)[0]
    
    def get_metadata_for_version(self, version: str) -> Dict[str, Any]:
        """Get metadata for a specific version.
        
        Args:
            version (str): Version string.
            
        Returns:
            Dict[str, Any]: Metadata for the specified version.
        """
        version_metadata = self.metadata.get('versions', {}).get(version, {})
        return version_metadata if version_metadata else self.metadata


class RegistryClient(ABC):
    """Abstract base class for registry clients.
    
    Defines the interface for interacting with different types of package
    registries (local files, remote APIs, etc.).
    """
    
    @abstractmethod
    def load_registry_data(self) -> bool:
        """Load registry data from the source.
        
        Returns:
            bool: True if loading was successful.
            
        Raises:
            RegistryError: If loading fails.
        """
        pass
    
    @abstractmethod
    def get_package_info(self, package_name: str) -> Optional[RegistryPackageInfo]:
        """Get information about a package.
        
        Args:
            package_name (str): Name of the package to look up.
            
        Returns:
            Optional[RegistryPackageInfo]: Package information, or None if not found.
        """
        pass
    
    @abstractmethod
    def package_exists(self, package_name: str) -> bool:
        """Check if a package exists in the registry.
        
        Args:
            package_name (str): Name of the package to check.
            
        Returns:
            bool: True if package exists.
        """
        pass
    
    @abstractmethod
    def get_all_packages(self) -> List[str]:
        """Get list of all package names in the registry.
        
        Returns:
            List[str]: List of all package names.
        """
        pass
    
    @abstractmethod
    def is_loaded(self) -> bool:
        """Check if registry data is loaded.
        
        Returns:
            bool: True if registry data is loaded.
        """
        pass


class LocalFileRegistryClient(RegistryClient):
    """Registry client that loads data from a local JSON file.
    
    Implements the RegistryClient interface for registries stored as local
    JSON files, such as the Hatch package registry.
    """
    
    def __init__(self, registry_file_path: str):
        """Initialize the local file registry client.
        
        Args:
            registry_file_path (str): Path to the registry JSON file.
        """
        self.registry_file_path = Path(registry_file_path)
        self.registry_data: Dict[str, Any] = {}
        self._loaded = False
    
    def load_registry_data(self) -> bool:
        """Load registry data from the local JSON file.
        
        Returns:
            bool: True if loading was successful.
            
        Raises:
            RegistryError: If file doesn't exist or contains invalid JSON.
        """
        try:
            if not self.registry_file_path.exists():
                raise RegistryError(f"Registry file not found: {self.registry_file_path}")
            
            with open(self.registry_file_path, 'r', encoding='utf-8') as f:
                self.registry_data = json.load(f)
            
            self._loaded = True
            return True
            
        except json.JSONDecodeError as e:
            raise RegistryError(f"Invalid JSON in registry file: {e}")
        except Exception as e:
            raise RegistryError(f"Error loading registry file: {e}")
    
    def get_package_info(self, package_name: str) -> Optional[RegistryPackageInfo]:
        """Get information about a package from the registry.
        
        Args:
            package_name (str): Name of the package to look up.
            
        Returns:
            Optional[RegistryPackageInfo]: Package information, or None if not found.
        """
        if not self._loaded:
            self.load_registry_data()
        
        # Handle different registry data structures
        packages = self.registry_data.get('packages', {})
        if package_name not in packages:
            return None
        
        package_data = packages[package_name]
        
        # Extract versions - handle different possible structures
        versions = []
        if isinstance(package_data, dict):
            if 'versions' in package_data:
                versions = list(package_data['versions'].keys())
            elif 'version' in package_data:
                versions = [package_data['version']]
        
        return RegistryPackageInfo(
            name=package_name,
            versions=versions,
            metadata=package_data
        )
    
    def package_exists(self, package_name: str) -> bool:
        """Check if a package exists in the registry.
        
        Args:
            package_name (str): Name of the package to check.
            
        Returns:
            bool: True if package exists.
        """
        if not self._loaded:
            self.load_registry_data()
        
        packages = self.registry_data.get('packages', {})
        return package_name in packages
    
    def get_all_packages(self) -> List[str]:
        """Get list of all package names in the registry.
        
        Returns:
            List[str]: List of all package names.
        """
        if not self._loaded:
            self.load_registry_data()
        
        packages = self.registry_data.get('packages', {})
        return list(packages.keys())
    
    def is_loaded(self) -> bool:
        """Check if registry data is loaded.
        
        Returns:
            bool: True if registry data is loaded.
        """
        return self._loaded
    
    def get_raw_registry_data(self) -> Dict[str, Any]:
        """Get the raw registry data.
        
        Returns:
            Dict[str, Any]: Raw registry data dictionary.
        """
        if not self._loaded:
            self.load_registry_data()
        return self.registry_data


class CachedRegistryClient(RegistryClient):
    """Registry client that adds caching capabilities to another client.
    
    Wraps another RegistryClient implementation and adds caching to improve
    performance when making repeated queries.
    """
    
    def __init__(self, base_client: RegistryClient):
        """Initialize the cached registry client.
        
        Args:
            base_client (RegistryClient): The underlying registry client to wrap.
        """
        self.base_client = base_client
        self._package_cache: Dict[str, Optional[RegistryPackageInfo]] = {}
        self._all_packages_cache: Optional[List[str]] = None
        self._cache_valid = False
    
    def load_registry_data(self) -> bool:
        """Load registry data and invalidate cache.
        
        Returns:
            bool: True if loading was successful.
            
        Raises:
            RegistryError: If loading fails.
        """
        result = self.base_client.load_registry_data()
        if result:
            self._invalidate_cache()
        return result
    
    def get_package_info(self, package_name: str) -> Optional[RegistryPackageInfo]:
        """Get information about a package with caching.
        
        Args:
            package_name (str): Name of the package to look up.
            
        Returns:
            Optional[RegistryPackageInfo]: Package information, or None if not found.
        """
        if not self._cache_valid or package_name not in self._package_cache:
            package_info = self.base_client.get_package_info(package_name)
            self._package_cache[package_name] = package_info
            self._cache_valid = True
        
        return self._package_cache[package_name]
    
    def package_exists(self, package_name: str) -> bool:
        """Check if a package exists with caching.
        
        Args:
            package_name (str): Name of the package to check.
            
        Returns:
            bool: True if package exists.
        """
        package_info = self.get_package_info(package_name)
        return package_info is not None
    
    def get_all_packages(self) -> List[str]:
        """Get list of all package names with caching.
        
        Returns:
            List[str]: List of all package names.
        """
        if not self._cache_valid or self._all_packages_cache is None:
            self._all_packages_cache = self.base_client.get_all_packages()
            self._cache_valid = True
        
        return self._all_packages_cache.copy()
    
    def is_loaded(self) -> bool:
        """Check if registry data is loaded.
        
        Returns:
            bool: True if registry data is loaded.
        """
        return self.base_client.is_loaded()
    
    def _invalidate_cache(self) -> None:
        """Invalidate all cached data."""
        self._package_cache.clear()
        self._all_packages_cache = None
        self._cache_valid = False
    
    def clear_cache(self) -> None:
        """Manually clear the cache."""
        self._invalidate_cache()


class RegistryManager:
    """Manager for registry clients and registry-related operations.
    
    Provides a high-level interface for working with package registries,
    including validation of package dependencies against registry data.
    """
    
    def __init__(self, registry_client: RegistryClient):
        """Initialize the registry manager.
        
        Args:
            registry_client (RegistryClient): Registry client to use.
        """
        self.registry_client = registry_client
    
    def validate_package_exists(self, package_name: str) -> Tuple[bool, Optional[str]]:
        """Validate that a package exists in the registry.
        
        Args:
            package_name (str): Name of the package to validate.
            
        Returns:
            Tuple[bool, Optional[str]]: A tuple containing:
                - bool: Whether the package exists
                - Optional[str]: Error message if validation fails, None otherwise
        """
        try:
            if not self.registry_client.is_loaded():
                self.registry_client.load_registry_data()
            
            if self.registry_client.package_exists(package_name):
                return True, None
            else:
                return False, f"Package '{package_name}' not found in registry"
                
        except RegistryError as e:
            return False, f"Registry error: {e}"
        except Exception as e:
            return False, f"Unexpected error checking package existence: {e}"
    
    def validate_package_version(self, package_name: str, version: str) -> Tuple[bool, Optional[str]]:
        """Validate that a specific version of a package exists.
        
        Args:
            package_name (str): Name of the package.
            version (str): Version to validate.
            
        Returns:
            Tuple[bool, Optional[str]]: A tuple containing:
                - bool: Whether the version exists
                - Optional[str]: Error message if validation fails, None otherwise
        """
        try:
            package_info = self.registry_client.get_package_info(package_name)
            if package_info is None:
                return False, f"Package '{package_name}' not found in registry"
            
            if package_info.has_version(version):
                return True, None
            else:
                available_versions = ', '.join(package_info.versions) if package_info.versions else 'none'
                return False, f"Version '{version}' of package '{package_name}' not found. Available versions: {available_versions}"
                
        except RegistryError as e:
            return False, f"Registry error: {e}"
        except Exception as e:
            return False, f"Unexpected error checking package version: {e}"
    
    def get_missing_packages(self, package_names: List[str]) -> List[str]:
        """Get list of packages that don't exist in the registry.
        
        Args:
            package_names (List[str]): List of package names to check.
            
        Returns:
            List[str]: List of package names that don't exist in the registry.
        """
        missing = []
        for package_name in package_names:
            exists, _ = self.validate_package_exists(package_name)
            if not exists:
                missing.append(package_name)
        return missing
    
    def validate_dependency_list(self, dependencies: List[str]) -> Tuple[bool, List[str]]:
        """Validate a list of package dependencies against the registry.
        
        Args:
            dependencies (List[str]): List of package names to validate.
            
        Returns:
            Tuple[bool, List[str]]: A tuple containing:
                - bool: Whether all dependencies are valid
                - List[str]: List of error messages (empty if all valid)
        """
        errors = []
        
        for package_name in dependencies:
            valid, error = self.validate_package_exists(package_name)
            if not valid:
                errors.append(error)
        
        return len(errors) == 0, errors
    
    def get_registry_statistics(self) -> Dict[str, int]:
        """Get statistics about the registry.
        
        Returns:
            Dict[str, int]: Dictionary containing registry statistics.
        """
        try:
            all_packages = self.registry_client.get_all_packages()
            total_packages = len(all_packages)
            
            total_versions = 0
            for package_name in all_packages:
                package_info = self.registry_client.get_package_info(package_name)
                if package_info:
                    total_versions += len(package_info.versions)
            
            return {
                'total_packages': total_packages,
                'total_versions': total_versions,
                'average_versions_per_package': total_versions / total_packages if total_packages > 0 else 0
            }
        except Exception:
            return {
                'total_packages': 0,
                'total_versions': 0,
                'average_versions_per_package': 0
            }
