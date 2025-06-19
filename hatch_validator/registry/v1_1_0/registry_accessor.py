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