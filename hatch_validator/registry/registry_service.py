"""Registry service for package registry operations.

Provides a high-level interface for working with package registries, including
validation of package dependencies against registry data.
"""

import logging
from packaging import specifiers
from typing import Optional, Dict, List, Any, Tuple

from .registry_accessor_factory import RegistryAccessorFactory
from .registry_accessor_base import RegistryAccessorBase, RegistryError
from hatch_validator.utils.version_utils import VersionConstraintValidator, VersionConstraintError

logger = logging.getLogger("hatch.registry_service")


class RegistryService:
    """Service for registry operations.

    Provides a high-level interface for working with package registries,
    including validation of package dependencies against registry data.
    This service uses the accessor chain pattern to handle different
    registry schema versions automatically.
    """
    
    def __init__(self, registry_data: Optional[Dict[str, Any]] = None):
        """Initialize the registry service.

        Args:
            registry_data (Dict[str, Any], optional): Initial registry data.
        """
        self._registry_data: Optional[Dict[str, Any]] = registry_data
        self._accessor: Optional[RegistryAccessorBase] = None
        if registry_data:
            self._accessor = RegistryAccessorFactory.create_accessor_for_data(registry_data)
    
    def load_registry_data(self, registry_data: Dict[str, Any]) -> None:
        """Load registry data and initialize appropriate accessor.

        Args:
            registry_data (Dict[str, Any]): Registry data to load.

        Raises:
            RegistryError: If no accessor can handle the registry data.
        """
        self._registry_data = registry_data
        self._accessor = RegistryAccessorFactory.create_accessor_for_data(registry_data)
        
        if not self._accessor:
            raise RegistryError("No accessor available for the provided registry data format")
        
        logger.debug(f"Loaded registry data with schema version: {self._accessor.get_schema_version(registry_data)}")
    
    def load_registry_from_file(self, file_path: str) -> None:
        """Load registry data from a JSON file.

        Args:
            file_path (str): Path to the registry JSON file.

        Raises:
            RegistryError: If file cannot be read or contains invalid data.
        """
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                registry_data = json.load(f)
            self.load_registry_data(registry_data)
        except (IOError, json.JSONDecodeError) as e:
            raise RegistryError(f"Failed to load registry from file {file_path}: {e}")
    
    def is_loaded(self) -> bool:
        """Check if registry data is loaded.

        Returns:
            bool: True if registry data is loaded and accessible.
        """
        return self._registry_data is not None and self._accessor is not None
    
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a package.

        Args:
            package_name (str): Name of the package to look up.

        Returns:
            Optional[Dict[str, Any]]: Package information as dictionary, or None if not found.
                Contains keys: name, versions, metadata

        Raises:
            RegistryError: If registry data is not loaded.
        """
        if not self.is_loaded():
            raise RegistryError("Registry data not loaded")
        
        if not self._accessor.package_exists(self._registry_data, package_name):
            logger.warning(f"Package '{package_name}' does not exist in the registry.")
            return None
        
        versions = self._accessor.get_package_versions(self._registry_data, package_name)
        metadata = self._accessor.get_package_metadata(self._registry_data, package_name)
        
        return {
            'name': package_name,
            'versions': versions,
            'metadata': metadata
        }
    
    def package_exists(self, package_name: str) -> bool:
        """Check if a package exists in the registry.

        Args:
            package_name (str): Name of the package to check.

        Returns:
            bool: True if package exists.

        Raises:
            RegistryError: If registry data is not loaded.
        """
        if not self.is_loaded():
            raise RegistryError("Registry data not loaded")
        
        return self._accessor.package_exists(self._registry_data, package_name)
    
    def get_package_versions(self, package_name: str) -> List[str]:
        """Get all versions for a package.

        Args:
            package_name (str): Package name.

        Returns:
            List[str]: List of version strings, empty if package not found.

        Raises:
            RegistryError: If registry data is not loaded.
            RegistryError: If package does not exist.
        """
        if not self.is_loaded():
            raise RegistryError("Registry data not loaded")
        
        if not self.package_exists(package_name):
            raise RegistryError(f"Package '{package_name}' does not exist in the registry")
                
        return self._accessor.get_package_versions(self._registry_data, package_name)
    
    def get_all_package_names(self) -> List[str]:
        """Get all package names from registry.

        Returns:
            List[str]: List of all package names, empty if registry not loaded.

        Raises:
            RegistryError: If registry data is not loaded.
        """
        if not self.is_loaded():
            raise RegistryError("Registry data not loaded")
        
        return self._accessor.get_all_package_names(self._registry_data)
    
    def get_package_dependencies(self, package_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """Get reconstructed dependencies for a specific package version.

        Args:
            package_name (str): Package name.
            version (str, optional): Specific version. If None, uses latest version.

        Returns:
            Dict[str, Any]: Reconstructed package metadata with dependencies.

        Raises:
            RegistryError: If registry data is not loaded.
        """
        if not self.is_loaded():
            raise RegistryError("Registry data not loaded")
        
        return self._accessor.get_package_dependencies(self._registry_data, package_name, version)
    
    def find_compatible_version(self, package_name: str, version_constraint: Optional[str] = None) -> Optional[str]:
        """Find a compatible version for a package given a version constraint.

        Args:
            package_name (str): Package name.
            version_constraint (str, optional): Version constraint (e.g., '>=1.0.0').

        Returns:
            Optional[str]: Compatible version string, or None if not found.

        Raises:
            RegistryError: If registry data is not loaded.
        """
        if not self.is_loaded():
            raise RegistryError("Registry data not loaded")
        
        if hasattr(self._accessor, 'find_compatible_version'):
            return self._accessor.find_compatible_version(self._registry_data, package_name, version_constraint)
        else:
            # Fallback for accessors without this method
            versions = self.get_package_versions(package_name)
            if not versions:
                return None
            if not version_constraint:
                return versions[-1]
            # Use VersionConstraintValidator to find a compatible version (prefer highest)
            compatible_versions = [
                v for v in sorted(versions, key=lambda x: tuple(int(p) if p.isdigit() else p for p in x.split('.')), reverse=True)
                if VersionConstraintValidator.is_version_compatible(v, version_constraint)[0]
            ]

            if not compatible_versions:
                raise VersionConstraintError(f"No compatible version found for '{package_name}' with constraint '{version_constraint}'")
        
            return compatible_versions[0]
    
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
            if not self.is_loaded():
                raise RegistryError("Registry data not loaded")
            
            if self.package_exists(package_name):
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
            if not self.is_loaded():
                raise RegistryError("Registry data not loaded")
            
            versions = self.get_package_versions(package_name)
            if not versions:
                return False, f"Package '{package_name}' not found in registry"
            
            if version in versions:
                return True, None
            else:
                available_versions = ', '.join(versions)
                return False, f"Version '{version}' of package '{package_name}' not found. Available versions: {available_versions}"
                
        except RegistryError as e:
            return False, f"Registry error: {e}"
        except Exception as e:
            return False, f"Unexpected error checking package version: {e}"
    
    def validate_version_compatibility(self, package_name: str, version_constraint: str) -> Tuple[bool, Optional[str]]:
        """Validate that a version constraint can be satisfied by available package versions.

        Args:
            package_name (str): Name of the package.
            version_constraint (str): Version constraint (e.g. '>=1.0.0').

        Returns:
            Tuple[bool, Optional[str]]: A tuple containing:
                - bool: Whether the constraint can be satisfied
                - Optional[str]: Error message if validation fails, None otherwise
        """
        try:
            if not self.is_loaded():
                raise RegistryError("Registry data not loaded")
            
            versions = self.get_package_versions(package_name)
            if not versions:
                return False, f"Package '{package_name}' not found in registry"
            
            # Use VersionConstraintValidator from utils
            for v in versions:
                is_compatible, error = VersionConstraintValidator.is_version_compatible(v, version_constraint)
                if is_compatible:
                    return True, None
            available_versions = ', '.join(versions)
            return False, f"No version of '{package_name}' satisfies constraint {version_constraint}. Available versions: {available_versions}"
                
        except Exception as e:
            return False, f"Error checking version compatibility: {e}"
    
    def get_missing_packages(self, package_names: List[str]) -> List[str]:
        """Get list of packages that don't exist in the registry.

        Args:
            package_names (List[str]): List of package names to check.

        Returns:
            List[str]: List of package names that don't exist in the registry.

        Raises:
            RegistryError: If registry data is not loaded.
        """
        if not self.is_loaded():
            raise RegistryError("Registry data not loaded")
        
        missing = []
        for package_name in package_names:
            if not self.package_exists(package_name):
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

        Raises:
            RegistryError: If registry data is not loaded.
        """
        if not self.is_loaded():
            raise RegistryError("Registry data not loaded")
        
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

        Raises:
            RegistryError: If registry data is not loaded.
        """
        try:
            if not self.is_loaded():
                raise RegistryError("Registry data not loaded")
            
            all_packages = self.get_all_package_names()
            total_packages = len(all_packages)
            
            total_versions = 0
            for package_name in all_packages:
                versions = self.get_package_versions(package_name)
                total_versions += len(versions)
            
            return {
                'total_packages': total_packages,
                'total_versions': total_versions,
                'average_versions_per_package': total_versions / total_packages if total_packages > 0 else 0
            }
        except RegistryError:
            return {
                'total_packages': 0,
                'total_versions': 0,
                'average_versions_per_package': 0
            }
        except Exception:
            return {
                'total_packages': 0,
                'total_versions': 0,
                'average_versions_per_package': 0
            }
    
    def get_registry_data(self) -> Optional[Dict[str, Any]]:
        """Get the raw registry data.

        Returns:
            Optional[Dict[str, Any]]: Registry data if available, None otherwise.

        Raises:
            RegistryError: If registry data is not loaded.
        """
        if not self.is_loaded():
            raise RegistryError("Registry data not loaded")
        return self._registry_data
    
    def get_schema_version(self) -> Optional[str]:
        """Get the schema version of the loaded registry data.

        Returns:
            Optional[str]: Schema version string, or None if no data loaded.

        Raises:
            RegistryError: If registry data is not loaded.
        """
        if not self.is_loaded():
            raise RegistryError("Registry data not loaded")
        return self._accessor.get_schema_version(self._registry_data)
    
    def list_repositories(self) -> List[str]:
        """List all repository names in the loaded registry.

        Returns:
            List[str]: List of repository names.
        Raises:
            RegistryError: If registry data is not loaded.
        """
        if not self.is_loaded():
            raise RegistryError("Registry data not loaded")
        return self._accessor.list_repositories(self._registry_data)

    def repository_exists(self, repo_name: str) -> bool:
        """Check if a repository exists in the loaded registry.

        Args:
            repo_name (str): Repository name.
        Returns:
            bool: True if repository exists.
        Raises:
            RegistryError: If registry data is not loaded.
        """
        if not self.is_loaded():
            raise RegistryError("Registry data not loaded")
        return self._accessor.repository_exists(self._registry_data, repo_name)

    def list_packages(self, repo_name: str) -> List[str]:
        """List all package names in a given repository.

        Args:
            repo_name (str): Repository name.
        Returns:
            List[str]: List of package names in the repository.
        Raises:
            RegistryError: If registry data is not loaded.
        """
        if not self.is_loaded():
            raise RegistryError("Registry data not loaded")
        return self._accessor.list_packages(self._registry_data, repo_name)

    def get_package_by_repo(self, repo_name: str, package_name: str) -> Optional[Dict[str, Any]]:
        """Get a package by repository and package name.

        Args:
            repo_name (str): Repository name.
            package_name (str): Package name.
        Returns:
            Optional[Dict[str, Any]]: Package metadata or None if not found.
        Raises:
            RegistryError: If registry data is not loaded.
        """
        if not self.is_loaded():
            raise RegistryError("Registry data not loaded")
        return self._accessor.get_package_by_repo(self._registry_data, repo_name, package_name)
