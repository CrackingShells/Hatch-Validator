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


class RegistryAccessor(ABC):
    """Abstract base class for version-specific registry data accessors.
    
    Implements the chain of responsibility pattern for handling different
    registry schema versions.
    """
    
    def __init__(self, successor: Optional['RegistryAccessor'] = None):
        """Initialize the registry accessor.
        
        Args:
            successor (Optional[RegistryAccessor]): Next accessor in the chain.
        """
        self._successor = successor
    
    @abstractmethod
    def can_handle(self, registry_data: Dict[str, Any]) -> bool:
        """Check if this accessor can handle the given registry data.
        
        Args:
            registry_data (Dict[str, Any]): Registry data to check.
            
        Returns:
            bool: True if this accessor can handle the data.
        """
        pass
    
    @abstractmethod
    def get_schema_version(self, registry_data: Dict[str, Any]) -> str:
        """Get the schema version from registry data.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            
        Returns:
            str: Schema version string.
        """
        pass
    
    @abstractmethod
    def get_all_package_names(self, registry_data: Dict[str, Any]) -> List[str]:
        """Get all package names from registry data.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            
        Returns:
            List[str]: List of package names.
        """
        pass
    
    @abstractmethod
    def package_exists(self, registry_data: Dict[str, Any], package_name: str) -> bool:
        """Check if a package exists in the registry.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name to check.
            
        Returns:
            bool: True if package exists.
        """
        pass
    
    @abstractmethod
    def get_package_versions(self, registry_data: Dict[str, Any], package_name: str) -> List[str]:
        """Get all versions for a package.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name.
            
        Returns:
            List[str]: List of version strings.
        """
        pass
    
    @abstractmethod
    def get_package_metadata(self, registry_data: Dict[str, Any], package_name: str) -> Dict[str, Any]:
        """Get metadata for a package.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name.
            
        Returns:
            Dict[str, Any]: Package metadata.
        """
        pass
    
    def handle_request(self, registry_data: Dict[str, Any]) -> Optional['RegistryAccessor']:
        """Handle the request using chain of responsibility pattern.
        
        Args:
            registry_data (Dict[str, Any]): Registry data to handle.
            
        Returns:
            Optional[RegistryAccessor]: Accessor that can handle the data, or None.
        """
        if self.can_handle(registry_data):
            return self
        elif self._successor:
            return self._successor.handle_request(registry_data)
        else:
            return None


class RegistryAccessorV1_1_0(RegistryAccessor):
    """Registry accessor for schema version 1.1.0.
    
    Handles the CrackingShells Package Registry format with repositories
    containing packages with versions.
    """
    
    def can_handle(self, registry_data: Dict[str, Any]) -> bool:
        """Check if this accessor can handle the given registry data.
        
        Args:
            registry_data (Dict[str, Any]): Registry data to check.
            
        Returns:
            bool: True if this accessor can handle the data.
        """
        schema_version = registry_data.get('registry_schema_version', '')
        return schema_version.startswith('1.1.')
    
    def get_schema_version(self, registry_data: Dict[str, Any]) -> str:
        """Get the schema version from registry data.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            
        Returns:
            str: Schema version string.
        """
        return registry_data.get('registry_schema_version', 'unknown')
    
    def get_all_package_names(self, registry_data: Dict[str, Any]) -> List[str]:
        """Get all package names from registry data.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            
        Returns:
            List[str]: List of package names.
        """
        package_names = []
        repositories = registry_data.get('repositories', [])
        
        for repo in repositories:
            packages = repo.get('packages', [])
            for package in packages:
                package_name = package.get('name')
                if package_name and package_name not in package_names:
                    package_names.append(package_name)
        
        return package_names
    
    def package_exists(self, registry_data: Dict[str, Any], package_name: str) -> bool:
        """Check if a package exists in the registry.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name to check.
            
        Returns:
            bool: True if package exists.
        """
        return package_name in self.get_all_package_names(registry_data)
    
    def get_package_versions(self, registry_data: Dict[str, Any], package_name: str) -> List[str]:
        """Get all versions for a package.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name.
            
        Returns:
            List[str]: List of version strings.
        """
        repositories = registry_data.get('repositories', [])
        
        for repo in repositories:
            packages = repo.get('packages', [])
            for package in packages:
                if package.get('name') == package_name:
                    versions = package.get('versions', [])
                    return [v.get('version') for v in versions if v.get('version')]
        
        return []
    
    def get_package_metadata(self, registry_data: Dict[str, Any], package_name: str) -> Dict[str, Any]:
        """Get metadata for a package.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name.
            
        Returns:
            Dict[str, Any]: Package metadata.
        """
        repositories = registry_data.get('repositories', [])
        
        for repo in repositories:
            packages = repo.get('packages', [])
            for package in packages:
                if package.get('name') == package_name:
                    return package
        
        return {}
    
    def get_package_dependencies(self, registry_data: Dict[str, Any], package_name: str, version: str = None) -> Dict[str, Any]:
        """Get reconstructed dependencies for a specific package version.
        
        This method reconstructs the complete dependency information from the differential
        storage format used in the registry.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name.
            version (str, optional): Specific version. If None, uses latest version.
            
        Returns:
            Dict[str, Any]: Reconstructed package metadata with complete dependency information.
                Contains keys: name, version, hatch_dependencies, python_dependencies, compatibility
        """
        package_data = self.get_package_metadata(registry_data, package_name)
        if not package_data:
            return {}
        
        versions = package_data.get('versions', [])
        if not versions:
            return {}
        
        # Find the specific version or use latest
        version_info = None
        if version:
            for v in versions:
                if v.get('version') == version:
                    version_info = v
                    break
        else:
            # Use latest version (last in list)
            version_info = versions[-1]
        
        if not version_info:
            return {}
        
        return self._reconstruct_package_version(package_data, version_info)
    
    def _reconstruct_package_version(self, package: Dict[str, Any], version_info: Dict[str, Any]) -> Dict[str, Any]:
        """Reconstruct complete package metadata for a specific version by walking the diff tree.
        
        This method follows the differential storage approach where each version contains
        only the changes from its base version.
        
        Args:
            package (Dict[str, Any]): Package object from the registry.
            version_info (Dict[str, Any]): Specific version information.
            
        Returns:
            Dict[str, Any]: Reconstructed package metadata including dependencies and compatibility.
        """
        # Build version chain from current version back to the base
        version_chain = []
        current_version = version_info
        package_versions = package.get("versions", [])
        
        while current_version:
            version_chain.append(current_version)
            base_version = current_version.get("base_version")
            
            if not base_version:
                break
                
            # Find the base version
            current_version = None
            for ver in package_versions:
                if ver.get("version") == base_version:
                    current_version = ver
                    break
        
        # Initialize with empty metadata
        reconstructed = {
            "name": package["name"],
            "version": version_info["version"],
            "hatch_dependencies": [],
            "python_dependencies": [],
            "compatibility": {}
        }
        
        # Apply changes from oldest to newest (reverse the chain)
        for ver in reversed(version_chain):
            # Process hatch dependencies
            # Add new dependencies
            for dep in ver.get("hatch_dependencies_added", []):
                reconstructed["hatch_dependencies"].append(dep)
            
            # Remove dependencies
            for dep_name in ver.get("hatch_dependencies_removed", []):
                reconstructed["hatch_dependencies"] = [
                    d for d in reconstructed["hatch_dependencies"] 
                    if d.get("name") != dep_name
                ]
            
            # Modify dependencies
            for mod_dep in ver.get("hatch_dependencies_modified", []):
                for i, dep in enumerate(reconstructed["hatch_dependencies"]):
                    if dep.get("name") == mod_dep.get("name"):
                        reconstructed["hatch_dependencies"][i] = mod_dep
                        break
            
            # Process Python dependencies
            # Add new dependencies
            for dep in ver.get("python_dependencies_added", []):
                reconstructed["python_dependencies"].append(dep)
            
            # Remove dependencies
            for dep_name in ver.get("python_dependencies_removed", []):
                reconstructed["python_dependencies"] = [
                    d for d in reconstructed["python_dependencies"] 
                    if d.get("name") != dep_name
                ]
            
            # Modify dependencies
            for mod_dep in ver.get("python_dependencies_modified", []):
                for i, dep in enumerate(reconstructed["python_dependencies"]):
                    if dep.get("name") == mod_dep.get("name"):
                        reconstructed["python_dependencies"][i] = mod_dep
                        break
            
            # Process compatibility info
            for key, value in ver.get("compatibility_changes", {}).items():
                reconstructed["compatibility"][key] = value
        
        return reconstructed
    
    def find_compatible_version(self, registry_data: Dict[str, Any], package_name: str, version_constraint: str = None) -> Optional[str]:
        """Find a compatible version for a package given a version constraint.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name.
            version_constraint (str, optional): Version constraint (e.g., '>=1.0.0').
            
        Returns:
            Optional[str]: Compatible version string, or None if not found.
        """
        from packaging import version, specifiers
        
        versions = self.get_package_versions(registry_data, package_name)
        if not versions:
            return None
        
        if not version_constraint:
            # Return latest version
            return versions[-1] if versions else None
        
        try:
            spec = specifiers.SpecifierSet(version_constraint)
            
            # Filter compatible versions
            compatible_versions = []
            for v in versions:
                if spec.contains(v):
                    compatible_versions.append(v)
            
            # Return the latest compatible version
            if compatible_versions:
                # Sort versions and return the latest
                compatible_versions.sort(key=lambda x: version.Version(x))
                return compatible_versions[-1]
            
        except Exception:
            pass
        
        return None
    

class LegacyRegistryAccessor(RegistryAccessor):
    """Registry accessor for legacy registry formats.
    
    Handles older registry formats with direct 'packages' structure.
    """
    
    def can_handle(self, registry_data: Dict[str, Any]) -> bool:
        """Check if this accessor can handle the given registry data.
        
        Args:
            registry_data (Dict[str, Any]): Registry data to check.
            
        Returns:
            bool: True if this accessor can handle the data.
        """
        # If it has a 'packages' key at root level and no schema version, assume legacy
        return 'packages' in registry_data and 'registry_schema_version' not in registry_data
    
    def get_schema_version(self, registry_data: Dict[str, Any]) -> str:
        """Get the schema version from registry data.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            
        Returns:
            str: Schema version string.
        """
        return 'legacy'
    
    def get_all_package_names(self, registry_data: Dict[str, Any]) -> List[str]:
        """Get all package names from registry data.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            
        Returns:
            List[str]: List of package names.
        """
        packages = registry_data.get('packages', {})
        return list(packages.keys())
    
    def package_exists(self, registry_data: Dict[str, Any], package_name: str) -> bool:
        """Check if a package exists in the registry.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name to check.
            
        Returns:
            bool: True if package exists.
        """
        packages = registry_data.get('packages', {})
        return package_name in packages
    
    def get_package_versions(self, registry_data: Dict[str, Any], package_name: str) -> List[str]:
        """Get all versions for a package.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name.
            
        Returns:
            List[str]: List of version strings.
        """
        packages = registry_data.get('packages', {})
        if package_name not in packages:
            return []
        
        package_data = packages[package_name]
        
        if isinstance(package_data, dict):
            if 'versions' in package_data:
                return list(package_data['versions'].keys())
            elif 'version' in package_data:
                return [package_data['version']]
        
        return []
    
    def get_package_metadata(self, registry_data: Dict[str, Any], package_name: str) -> Dict[str, Any]:
        """Get metadata for a package.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name.
            
        Returns:
            Dict[str, Any]: Package metadata.
        """
        packages = registry_data.get('packages', {})
        return packages.get(package_name, {})


class RegistryAccessorChain:
    """Chain of responsibility manager for registry accessors.
    
    Manages the chain of registry accessors and provides a unified interface
    for accessing registry data regardless of schema version.
    """
    
    def __init__(self):
        """Initialize the accessor chain."""
        # Build the chain with most recent versions first
        self.chain = RegistryAccessorV1_1_0(
            LegacyRegistryAccessor()
        )
    
    def get_accessor(self, registry_data: Dict[str, Any]) -> Optional[RegistryAccessor]:
        """Get the appropriate accessor for the given registry data.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            
        Returns:
            Optional[RegistryAccessor]: Appropriate accessor, or None if unsupported.
        """
        return self.chain.handle_request(registry_data)
    
    def get_supported_versions(self) -> List[str]:
        """Get list of supported schema versions.
        
        Returns:
            List[str]: List of supported version strings.
        """
        return ['1.1.0', 'legacy']


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
