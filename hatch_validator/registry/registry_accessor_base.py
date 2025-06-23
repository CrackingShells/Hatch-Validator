from typing import Dict, List, Set, Tuple, Optional, Any
from abc import ABC, abstractmethod

class RegistryError(Exception):
    """Exception raised for registry-related errors."""
    pass


class RegistryAccessorBase(ABC):
    """Abstract base class for version-specific registry data accessors.
    
    Implements the chain of responsibility pattern for handling different
    registry schema versions.
    """
    
    def __init__(self, successor: Optional['RegistryAccessorBase'] = None):
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
    def get_all_package_names(self, registry_data: Dict[str, Any], repo_name: Optional[str] = None) -> List[str]:
        """Get all package names from registry data.

        Args:
            registry_data (Dict[str, Any]): Registry data.
            repo_name (str, optional): Repository name. If None, returns all packages across all repositories.

        Returns:
            List[str]: List of package names.
        """
        pass
    
    @abstractmethod
    def package_exists(self, registry_data: Dict[str, Any], package_name: str, repo_name: Optional[str] = None) -> bool:
        """Check if a package exists in the registry.

        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name to check.
            repo_name (str, optional): Repository name. If None, uses default repository.

        Returns:
            bool: True if package exists.
        """
        pass
    
    @abstractmethod
    def get_package_versions(self, registry_data: Dict[str, Any], package_name: str, repo_name: Optional[str] = None) -> List[str]:
        """Get all versions for a package.

        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name.
            repo_name (str, optional): Repository name. If None, uses default repository.

        Returns:
            List[str]: List of version strings.
        """
        pass
    
    @abstractmethod
    def get_package_metadata(self, registry_data: Dict[str, Any], package_name: str, repo_name: Optional[str] = None) -> Dict[str, Any]:
        """Get metadata for a package.

        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name.
            repo_name (str, optional): Repository name. If None, uses default repository.

        Returns:
            Dict[str, Any]: Package metadata.
        """
        pass
    
    @abstractmethod
    def get_package_by_repo(self, registry_data: Dict[str, Any], repo_name: str, package_name: str) -> Optional[Dict[str, Any]]:
        """Get a package by repository and package name.

        Args:
            registry_data (Dict[str, Any]): Registry data.
            repo_name (str): Repository name.
            package_name (str): Package name.
        Returns:
            Optional[Dict[str, Any]]: Package metadata or None if not found.
        """
        pass

    @abstractmethod
    def get_package_dependencies(self, registry_data: Dict[str, Any], package_name: str, version: str = None, repo_name: Optional[str] = None) -> Dict[str, Any]:
        """Get reconstructed HATCH dependencies for a specific package version.
        
        This method reconstructs the complete dependency information from the differential
        storage format used in the registry.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name.
            version (str, optional): Specific version. If None, uses latest version.
            repo_name (str, optional): Repository name. If None, uses default repository.

        Returns:
            Dict[str, Any]: Reconstructed package metadata with complete dependency information.
                Contains keys: name, version, dependencies (hatch)
        """
        pass

    @abstractmethod
    def list_repositories(self, registry_data: Dict[str, Any]) -> List[str]:
        """List all repository names in the registry.

        Args:
            registry_data (Dict[str, Any]): Registry data.
        
        Returns:
            List[str]: List of repository names.
        """
        pass

    @abstractmethod
    def repository_exists(self, registry_data: Dict[str, Any], repo_name: str) -> bool:
        """Check if a repository exists in the registry.

        Args:
            registry_data (Dict[str, Any]): Registry data.
            repo_name (str): Repository name.
        
        Returns:
            bool: True if repository exists.
        """
        pass

    @abstractmethod
    def list_packages(self, registry_data: Dict[str, Any], repo_name: str) -> List[str]:
        """List all package names in a given repository.

        Args:
            registry_data (Dict[str, Any]): Registry data.
            repo_name (str): Repository name.
        
        Returns:
            List[str]: List of package names in the repository.
        """
        pass

    def handle_request(self, registry_data: Dict[str, Any]) -> Optional['RegistryAccessorBase']:
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