from typing import Dict, List, Any, Optional
from hatch_validator.registry.registry_accessor_base import RegistryAccessorBase
from hatch_validator.utils.version_utils import VersionConstraintValidator

class RegistryAccessor(RegistryAccessorBase):
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
        """Get all package names from all repositories in the registry data.

        Args:
            registry_data (Dict[str, Any]): Registry data.
        Returns:
            List[str]: List of package names.
        """
        package_names = []
        for repo in registry_data.get('repositories', []):
            for package in repo.get('packages', []):
                name = package.get('name')
                if name:
                    package_names.append(name)
        return package_names

    def package_exists(self, registry_data: Dict[str, Any], package_name: str, repo_name: Optional[str] = None) -> bool:
        """Check if a package exists in the registry, optionally in a specific repo.

        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name to check.
            repo_name (str, optional): Repository name. If None, search all repos.
        Returns:
            bool: True if package exists.
        """
        if repo_name:
            return package_name in self.list_packages(registry_data, repo_name)
        return package_name in self.get_all_package_names(registry_data)

    def get_package_versions(self, registry_data: Dict[str, Any], package_name: str, repo_name: Optional[str] = None) -> List[str]:
        """Get all versions for a package, optionally in a specific repo.

        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name.
            repo_name (str, optional): Repository name. If None, search all repos.
        Returns:
            List[str]: List of version strings.
        """
        repos = registry_data.get('repositories', [])
        for repo in repos:
            if repo_name and repo.get('name') != repo_name:
                continue
            for pkg in repo.get('packages', []):
                if pkg.get('name') == package_name:
                    return [ver.get('version') for ver in pkg.get('versions', []) if ver.get('version')]
        return []

    def get_package_metadata(self, registry_data: Dict[str, Any], package_name: str, repo_name: Optional[str] = None) -> Dict[str, Any]:
        """Get metadata for a package, optionally in a specific repo.

        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name.
            repo_name (str, optional): Repository name. If None, search all repos.
        Returns:
            Dict[str, Any]: Package metadata.
        """
        repos = registry_data.get('repositories', [])
        for repo in repos:
            if repo_name and repo.get('name') != repo_name:
                continue
            for pkg in repo.get('packages', []):
                if pkg.get('name') == package_name:
                    return pkg
        return {}

    def get_package_dependencies(self, registry_data: Dict[str, Any], package_name: str, version: str = None) -> Dict[str, Any]:
        """Get reconstructed HATCH dependencies for a specific package version.
        
        This method reconstructs the complete dependency information from the differential
        storage format used in the registry.
        
        Args:
            registry_data (Dict[str, Any]): Registry data.
            package_name (str): Package name.
            version (str, optional): Specific version. If None, uses latest version.
            
        Returns:
            Dict[str, Any]: Reconstructed package metadata with complete dependency information.
                Contains keys: name, version, dependencies (hatch)
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
                - Contains keys: name, version, dependencies (hatch)
        """
        version_chain = []
        package_versions = package.get("versions", [])
        
        # Initialize with empty metadata
        reconstructed = {
            "name": package["name"],
            "version": version_info["version"],
            "dependencies": []
        }
        
        # Apply changes from oldest to newest (reverse the chain)
        # Given that new versions are always appended to the end of the list during package updates,
        # we can iterate from the start.
        for ver in package_versions:
            # Process hatch dependencies
            # Add new dependencies
            for dep in ver.get("hatch_dependencies_added", []):
                reconstructed["dependencies"].append(dep)
            
            # Remove dependencies
            for dep_name in ver.get("hatch_dependencies_removed", []):
                reconstructed["dependencies"] = [
                    d for d in reconstructed["dependencies"]
                    if d.get("name") != dep_name
                ]
            
            # Modify dependencies
            for mod_dep in ver.get("hatch_dependencies_modified", []):
                for i, dep in enumerate(reconstructed["dependencies"]):
                    if dep.get("name") == mod_dep.get("name"):
                        reconstructed["dependencies"][i] = mod_dep
                        break
        
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
        versions = self.get_package_versions(registry_data, package_name)
        if not versions:
            return None

        if not version_constraint:
            # Return latest version
            return versions[-1] if versions else None

        # Use VersionConstraintValidator to filter compatible versions (prefer highest)
        compatible_versions = [
            v for v in sorted(versions, key=lambda x: tuple(int(p) if p.isdigit() else p for p in x.split('.')), reverse=True)
            if VersionConstraintValidator.is_version_compatible(v, version_constraint)[0]
        ]
        return compatible_versions[0] if compatible_versions else None

    def get_package_by_repo(self, registry_data: Dict[str, Any], repo_name: str, package_name: str) -> Optional[Dict[str, Any]]:
        """Get a package by repository and package name.

        Args:
            registry_data (Dict[str, Any]): Registry data.
            repo_name (str): Repository name.
            package_name (str): Package name.
        Returns:
            Optional[Dict[str, Any]]: Package metadata or None if not found.
        """
        for repo in registry_data.get('repositories', []):
            if repo.get('name') == repo_name:
                for pkg in repo.get('packages', []):
                    if pkg.get('name') == package_name:
                        return pkg
        return None

    def list_repositories(self, registry_data: Dict[str, Any]) -> List[str]:
        """List all repository names in the registry.

        Args:
            registry_data (Dict[str, Any]): Registry data.
        
        Returns:
            List[str]: List of repository names.
        """
        return [repo.get('name') for repo in registry_data.get('repositories', [])]

    def repository_exists(self, registry_data: Dict[str, Any], repo_name: str) -> bool:
        """Check if a repository exists in the registry.

        Args:
            registry_data (Dict[str, Any]): Registry data.
            repo_name (str): Repository name.
        
        Returns:
            bool: True if repository exists.
        """
        return any(repo.get('name') == repo_name for repo in registry_data.get('repositories', []))

    def list_packages(self, registry_data: Dict[str, Any], repo_name: str) -> List[str]:
        """List all package names in a given repository.

        Args:
            registry_data (Dict[str, Any]): Registry data.
            repo_name (str): Repository name.
        
        Returns:
            List[str]: List of package names in the repository.
        """
        for repo in registry_data.get('repositories', []):
            if repo.get('name') == repo_name:
                return [pkg.get('name') for pkg in repo.get('packages', [])]
        return []