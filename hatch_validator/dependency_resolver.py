import json
import logging
import re
from pathlib import Path
from collections import deque
from typing import Dict, List, Set, Tuple, Any, Optional
from packaging import version, specifiers

class DependencyResolutionError(Exception):
    """Exception raised for dependency resolution errors."""
    pass

class DependencyResolver:
    """
    Unified dependency resolver that handles both local package dependencies 
    and registry-based dependency resolution.
    """
    
    def __init__(self, registry_data=None):
        """Initialize the Dependency resolver.
        
        Args:
            registry_data: Registry data to use for dependency resolution
        """
        self.logger = logging.getLogger("hatch.dependency_resolver")
        self.logger.setLevel(logging.INFO)
        self.registry_data = registry_data
        self._package_cache = {}  # Cache for reconstructed package data
    
    def _parse_version_constraint(self, version_spec: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse a version constraint string into operator and version"""
        if not version_spec:
            return None, None
            
        match = re.match(r'^([<>=!~]+)(\d+(?:\.\d+)*)$', version_spec)
        if not match:
            raise DependencyResolutionError(f"Invalid version constraint: {version_spec}")
        return match.groups()
    
    def validate_version_constraint(self, dep_name: str, version_constraint: str) -> Tuple[bool, Optional[str]]:
        """
        Validate the syntax of a version constraint.
        
        Args:
            dep_name: Name of the dependency
            version_constraint: Version constraint string to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        if not version_constraint:
            return True, None
            
        try:
            specifiers.SpecifierSet(version_constraint)
            return True, None
        except Exception as e:
            error_msg = f"Invalid version constraint '{version_constraint}' for '{dep_name}': {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
            
    def is_version_compatible(self, installed_version: str, version_constraint: str) -> bool:
        """
        Check if an installed version is compatible with a requirement.
        
        Args:
            installed_version: The installed version
            version_constraint: The version constraint (e.g. '>=1.0.0')
            
        Returns:
            bool: True if compatible, False otherwise
        """
        if not version_constraint:
            return True
            
        try:
            req_spec = specifiers.SpecifierSet(version_constraint)
            return req_spec.contains(installed_version)
        except Exception as e:
            self.logger.error(f"Error checking version compatibility: {e}")
            return False
    
    def _get_local_package_metadata(self, package_path: Path) -> Dict:
        """Load and return metadata from a local package directory"""
        metadata_path = package_path / "hatch_metadata.json"
        if not metadata_path.exists():
            raise DependencyResolutionError(f"Metadata file not found: {metadata_path}")
        
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise DependencyResolutionError(f"Invalid metadata JSON: {e}")
        except Exception as e:
            raise DependencyResolutionError(f"Error reading metadata: {e}")
    
    def validate_dependencies(self, dependencies: List[Dict], 
                            package_dir: Optional[Path] = None) -> Tuple[bool, List[str]]:
        """
        Validate all dependencies (local and remote) using registry data as source of truth.
        
        Args:
            dependencies: List of all dependency definitions
            package_dir: Optional base directory for resolving file:// URIs
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, errors)
        """
        errors = []
        to_validate = deque(dependencies)  # Use a queue
        validated = set()  # Track processed dependencies by name
        is_valid = True
        
        if not self.registry_data:
            self.logger.warning("No registry data available for remote dependency validation")
        
        while to_validate:
            dep = to_validate.popleft()
            dep_name = dep.get('name')
            
            if not dep_name:
                errors.append(f"Dependency missing required 'name' field: {dep}")
                is_valid = False
                continue
            
            # Skip if already validated
            if dep_name in validated:
                continue
                
            validated.add(dep_name)
            
            # Validate version constraint first
            version_constraint = dep.get('version_constraint')
            constraint_valid, constraint_error = self.validate_version_constraint(dep_name, version_constraint)
            if not constraint_valid:
                errors.append(constraint_error)
                is_valid = False
                continue
                
            # Handle dependency based on type
            dep_type = dep.get('type', 'remote')
            
            if dep_type == 'local':
                local_valid, local_dep_errors, transitive_deps = self._validate_local_dependency(dep, package_dir)
                if not local_valid:
                    errors.extend(local_dep_errors)
                    is_valid = False
                
                # Add transitive dependencies to the queue
                for trans_dep in transitive_deps:
                    if trans_dep.get('name') not in validated:
                        to_validate.append(trans_dep)
                        
            elif dep_type == 'remote':
                remote_valid, remote_dep_errors = self._validate_remote_dependency(dep)
                if not remote_valid:
                    errors.extend(remote_dep_errors)
                    is_valid = False
                    
        return is_valid, errors
    
    def _validate_local_dependency(self, dep: Dict, base_dir: Optional[Path] = None) -> Tuple[bool, List[str], List[Dict]]:
        """
        Validate a local dependency and return any transitive dependencies.
        
        Args:
            dep: Local dependency definition
            base_dir: Optional base directory for resolving file:// URIs
            
        Returns:
            Tuple[bool, List[str], List[Dict]]: (is_valid, errors, transitive_dependencies)
        """
        errors = []
        is_valid = True
        transitive_deps = []
        
        dep_name = dep.get('name')
        uri = dep.get('uri')
        version_constraint = dep.get('version_constraint')

        self.logger.debug(f"Validating local dependency '{dep_name}' (version {version_constraint}) with URI '{uri}'")
        
        # Validate URI exists
        if not uri:
            error_msg = f"Local dependency '{dep_name}' is missing required field 'uri'"
            self.logger.error(error_msg)
            errors.append(error_msg)
            return False, errors, []
            
        # Check URI format
        if not uri.startswith('file://'):
            error_msg = f"Local dependency URI must start with 'file://' for '{dep_name}'"
            self.logger.error(error_msg)
            errors.append(error_msg)
            return False, errors, []
            
        # Extract path and resolve relative to base_dir if provided
        path_str = uri[7:]  # Remove "file://"
        path = Path(path_str)
        if base_dir and not path.is_absolute():
            path = base_dir / path
            
        # Check path exists
        if not path.exists() or not path.is_dir():
            error_msg = f"Local dependency path does not exist: {uri}"
            self.logger.error(error_msg)
            errors.append(error_msg)
            return False, errors, []
            
        try:
            # Load metadata and extract transitive dependencies
            metadata = self._get_local_package_metadata(path)
                
            # Check version compatibility
            local_version = metadata.get('version')
            if version_constraint and local_version:
                if not self.is_version_compatible(local_version, version_constraint):
                    error_msg = f"Local dependency '{dep_name}' version {local_version} does not satisfy constraint {version_constraint}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
                    is_valid = False
            
            # Get dependencies from this local package
            transitive_deps = metadata.get('hatch_dependencies', [])
                
        except DependencyResolutionError as e:
            errors.append(str(e))
            return False, errors, []
        except Exception as e:
            errors.append(f"Error validating local dependency '{dep_name}': {str(e)}")
            return False, errors, []
            
        return is_valid, errors, transitive_deps
    
    def _validate_remote_dependency(self, dep: Dict) -> Tuple[bool, List[str]]:
        """
        Validate a remote dependency against registry data.
        
        Args:
            dep: Remote dependency definition
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, errors)
        """
        errors = []
        is_valid = True
        
        dep_name = dep.get('name')
        version_constraint = dep.get('version_constraint')

        self.logger.debug(f"Validating remote dependency '{dep_name}' (version {version_constraint})")
        
        # Check if registry data is available
        if not self.registry_data:
            error_msg = f"No registry data available to validate remote dependency '{dep_name}'"
            self.logger.error(error_msg)
            errors.append(error_msg)
            return False, errors
        
        # Find the package in registry
        package_data = self.find_package_in_registry(dep_name)
        if not package_data:
            error_msg = f"Remote dependency '{dep_name}' not found in registry"
            self.logger.error(error_msg)
            errors.append(error_msg)
            return False, errors
            
        # If version constraint is provided, check compatibility
        if version_constraint:
            version_data = self.get_package_version(dep_name, version_constraint)
            if not version_data:
                error_msg = f"No version of '{dep_name}' satisfies constraint {version_constraint}"
                self.logger.error(error_msg)
                errors.append(error_msg)
                is_valid = False
            else:
                self.logger.debug(f"Found compatible version {version_data['version']} for '{dep_name}'")
                    
        return is_valid, errors
    
    def _build_dependency_graph(self, dependencies: List[Dict], 
                              package_dir: Optional[Path] = None,
                              pending_update: Optional[Tuple[str, Dict]] = None) -> Dict[str, List[str]]:
        """
        Build a complete dependency graph from initial dependencies using registry data.
        
        Args:
            dependencies: List of dependency definitions
            package_dir: Optional base directory for resolving file:// URIs
            pending_update: Optional tuple (pkg_name, metadata) with pending update information
            
        Returns:
            Dict[str, List[str]]: Graph as adjacency list (name -> list of dependencies)
        """
        dependency_graph = {}  # name -> list of dependencies
        unprocessed = deque([(dep.get('name'), dep) for dep in dependencies if dep.get('name')])
        processed = set()
        
        # Store pending update information if provided
        pending_pkg_name = None
        pending_metadata = None
        if pending_update:
            pending_pkg_name, pending_metadata = pending_update
        
        while unprocessed:
            self.logger.debug(f"Unprocessed: {unprocessed}")
            self.logger.debug(f"Processed: {processed}")

            dep_name, dep_info = unprocessed.popleft()
            
            if dep_name in processed:
                continue
                
            processed.add(dep_name)
            dependency_graph[dep_name] = []
            
            # Handle based on dependency type
            dep_type = dep_info.get('type', 'remote')
            
            if dep_type == 'local':
                # Extract transitive dependencies from local package
                uri = dep_info.get('uri')
                if uri and uri.startswith('file://'):
                    try:
                        # Get path
                        path_str = uri[7:]  # Remove "file://"
                        path = Path(path_str)
                        if package_dir and not path.is_absolute():
                            path = package_dir / path
                            
                        # Get metadata
                        metadata = self._get_local_package_metadata(path)
                        transitive_deps = metadata.get('hatch_dependencies', [])
                        
                        # Add dependencies to the graph
                        for d in transitive_deps:
                            d_name = d.get('name')
                            if d_name:
                                dependency_graph[dep_name].append(d_name)
                                
                                # Add to unprocessed if not already processed
                                if d_name not in processed:
                                    unprocessed.append((d_name, d))
                    except Exception as e:
                        self.logger.debug(f"Error processing local dependency '{dep_name}': {str(e)}")
            
            # For remote dependencies, use registry data
            else:
                try:
                    # Check if this is the pending update package
                    if pending_pkg_name and dep_name == pending_pkg_name:
                        # Use the pending metadata instead of registry data
                        next_deps = pending_metadata.get('hatch_dependencies', [])
                        
                        # Add to graph
                        for d in next_deps:
                            d_name = d.get('name')
                            if d_name:
                                dependency_graph[dep_name].append(d_name)
                                
                                # Add to unprocessed queue
                                if d_name not in processed:
                                    unprocessed.append((d_name, d))
                    else:
                        # Get latest version or matching version from registry
                        version_constraint = dep_info.get('version_constraint')
                        version_data = self.get_package_version(dep_name, version_constraint)
                        
                        if version_data:
                            # Reconstruct full dependencies from registry data
                            package_data = self.find_package_in_registry(dep_name)
                            if package_data:
                                # Get dependencies for this version
                                deps_data = self.get_full_package_dependencies(dep_name, version_data["version"])
                                next_deps = deps_data.get("dependencies", [])
                                
                                # Add to graph
                                for d in next_deps:
                                    d_name = d.get('name')
                                    if d_name:
                                        dependency_graph[dep_name].append(d_name)
                                        
                                        # Add to unprocessed queue
                                        if d_name not in processed:
                                            unprocessed.append((d_name, d))
                except Exception as e:
                    self.logger.debug(f"Error processing remote dependency '{dep_name}' from registry: {str(e)}")
        
        self.logger.debug(f"Final dependency graph: {dependency_graph}")

        return dependency_graph
    
    def detect_dependency_cycles(self, dependencies: List[Dict], 
                               package_dir: Optional[Path] = None,
                               pending_update: Optional[Tuple[str, Dict]] = None) -> Tuple[bool, List[List[str]]]:
        """
        Detect circular dependencies in the dependency graph using registry data.
        
        Args:
            dependencies: List of dependency definitions
            package_dir: Optional base directory for resolving file:// URIs
            pending_update: Optional tuple (pkg_name, metadata) with pending update information
            
        Returns:
            Tuple[bool, List[List[str]]]: (has_cycles, list_of_cycles)
        """
        # Build complete dependency graph first
        dependency_graph = self._build_dependency_graph(dependencies, package_dir, pending_update)
        cycles = []
        
        # Helper function to find cycles using DFS
        def find_cycles_for_node(node: str) -> bool:
            path = []
            visited = set()
            
            def dfs(current: str) -> bool:
                if current in path:
                    # Found a cycle
                    cycle_start = path.index(current)
                    cycles.append(path[cycle_start:] + [current])
                    return True
                    
                if current in visited:
                    return False
                    
                visited.add(current)
                path.append(current)
                
                has_cycle = False
                for neighbor in dependency_graph.get(current, []):
                    if dfs(neighbor):
                        has_cycle = True
                
                path.pop()  # Backtrack
                return has_cycle
                
            return dfs(node)
        
        # Check each node for cycles
        has_cycles = False
        for node in dependency_graph:
            if find_cycles_for_node(node):
                has_cycles = True
        self.logger.debug(f"Detected cycles: {cycles}")
        return has_cycles, cycles
    
    def get_full_package_dependencies(self, package_name: str, version: str) -> Dict:
        """
        Get the full dependency information for a specific package version by
        reconstructing it from differential storage in the registry.
        
        Args:
            package_name: Name of the package
            version: Version of the package
            
        Returns:
            Dict containing:
                - dependencies: List of Hatch package dependencies with version constraints
                - python_dependencies: List of Python package dependencies
                - compatibility: Dict with hatchling and python version requirements
        """
        if not self.registry_data:
            raise DependencyResolutionError("Registry data is required for this operation")
            
        # Find the package in the registry
        package_data = None
        version_data = None
        
        for repo in self.registry_data.get("repositories", []):
            for pkg in repo.get("packages", []):
                if pkg["name"] == package_name:
                    package_data = pkg
                    for ver in pkg.get("versions", []):
                        if ver["version"] == version:
                            version_data = ver
                            break
                    break
            if package_data:
                break
                
        if not package_data or not version_data:
            self.logger.error(f"Package {package_name} version {version} not found in registry")
            return {"dependencies": [], "python_dependencies": [], "compatibility": {}}
        
        # Reconstruct the full dependency data by applying differential changes
        return self._reconstruct_dependencies(package_data, version_data)
    
    def _reconstruct_dependencies(self, package_data: Dict, version_data: Dict) -> Dict:
        """
        Reconstruct full dependency information by walking back through version chain
        and applying all differential changes.
        
        Args:
            package_data: Package data from registry
            version_data: Specific version data from registry
            
        Returns:
            Dict with full dependency information
        """
        # Initialize with empty collections
        dependencies = {}  # name -> constraint
        python_dependencies = {}  # name -> {constraint, package_manager}
        compatibility = {}
        
        # Get the version chain by following base_version references
        version_chain = self._get_version_chain(package_data, version_data)
        
        # Apply all changes in the version chain from oldest to newest
        for ver in version_chain:
            # Process Hatch dependencies
            for dep in ver.get("hatch_dependencies_added", []):
                dependencies[dep["name"]] = dep.get("version_constraint", "")
                
            for dep_name in ver.get("hatch_dependencies_removed", []):
                if dep_name in dependencies:
                    del dependencies[dep_name]
                    
            for dep in ver.get("hatch_dependencies_modified", []):
                if dep["name"] in dependencies:
                    dependencies[dep["name"]] = dep.get("version_constraint", "")
            
            # Process Python dependencies
            for dep in ver.get("python_dependencies_added", []):
                python_dependencies[dep["name"]] = {
                    "version_constraint": dep.get("version_constraint", ""),
                    "package_manager": dep.get("package_manager", "pip")
                }
                
            for dep_name in ver.get("python_dependencies_removed", []):
                if dep_name in python_dependencies:
                    del python_dependencies[dep_name]
                    
            for dep in ver.get("python_dependencies_modified", []):
                if dep["name"] in python_dependencies:
                    python_dependencies[dep["name"]] = {
                        "version_constraint": dep.get("version_constraint", ""),
                        "package_manager": dep.get("package_manager", python_dependencies[dep["name"]].get("package_manager", "pip"))
                    }
            
            # Process compatibility changes
            if "compatibility_changes" in ver:
                compat_changes = ver["compatibility_changes"]
                if "hatchling" in compat_changes:
                    compatibility["hatchling"] = compat_changes["hatchling"]
                if "python" in compat_changes:
                    compatibility["python"] = compat_changes["python"]
        
        # Convert dictionaries back to lists for the expected return format
        deps_list = [{"name": name, "version_constraint": constraint} 
                    for name, constraint in dependencies.items()]
        
        python_deps_list = [
            {
                "name": name, 
                "version_constraint": info["version_constraint"],
                "package_manager": info["package_manager"]
            } 
            for name, info in python_dependencies.items()
        ]
        
        return {
            "dependencies": deps_list,
            "python_dependencies": python_deps_list,
            "compatibility": compatibility
        }
    
    def _get_version_chain(self, package_data: Dict, version_data: Dict) -> List[Dict]:
        """
        Build the chain of versions from the first version to the requested version.
        This is used to apply differential changes in sequence.
        
        Args:
            package_data: Package data from registry
            version_data: Starting version data
            
        Returns:
            List of version data objects ordered from oldest to newest
        """
        chain = [version_data]
        current = version_data
        
        # Keep looking up base versions until we reach a version with no base (the first version)
        while "base_version" in current and current["base_version"]:
            base_version = current["base_version"]
            found = False
            
            for ver in package_data.get("versions", []):
                if ver["version"] == base_version:
                    chain.append(ver)
                    current = ver
                    found = True
                    break
            
            if not found:
                self.logger.error(f"Base version {base_version} not found in package {package_data['name']}")
                break
        
        # Reverse to get oldest first
        chain.reverse()
        return chain
    
    def load_registry_data(self, registry_path: str) -> bool:
        """
        Load registry data from a file.
        
        Args:
            registry_path: Path to the registry JSON file
            
        Returns:
            bool: True if registry was successfully loaded
        """
        try:
            with open(registry_path, 'r') as f:
                self.registry_data = json.load(f)
            return True
        except Exception as e:
            self.logger.error(f"Failed to load registry: {e}")
            self.registry_data = {"repositories": []}
            return False
    
    def find_package_in_registry(self, package_name: str) -> Optional[Dict]:
        """
        Find a package in the registry data.
        
        Args:
            package_name: Name of the package to find
            
        Returns:
            Optional[Dict]: Package data if found, None otherwise
        """
        if not self.registry_data:
            self.logger.error("No registry data provided")
            return None
            
        for repo in self.registry_data.get("repositories", []):
            for pkg in repo.get("packages", []):
                if pkg["name"] == package_name:
                    return pkg
        
        return None
        
    def get_package_version(self, package_name: str, version_constraint: str = None) -> Optional[Dict]:
        """
        Get package version data from registry that satisfies the given constraint.
        If no constraint is provided, returns the latest version.
        
        Args:
            package_name: Name of the package
            version_constraint: Optional version constraint
            
        Returns:
            Optional[Dict]: Version data if found, None otherwise
        """
        package_data = self.find_package_in_registry(package_name)
        if not package_data:
            return None
            
        if not version_constraint:
            # Return the latest version
            latest_version = package_data.get("latest_version")
            if not latest_version:
                return None
                
            for ver_data in package_data.get("versions", []):
                if ver_data["version"] == latest_version:
                    return ver_data
            return None
        
        # Find a version that satisfies the constraint
        try:
            req_spec = specifiers.SpecifierSet(version_constraint)
            valid_versions = []
            
            for ver_data in package_data.get("versions", []):
                if req_spec.contains(ver_data["version"]):
                    valid_versions.append((ver_data["version"], ver_data))
                    
            if not valid_versions:
                return None
                
            # Return the highest matching version
            valid_versions.sort(key=lambda x: version.parse(x[0]), reverse=True)
            return valid_versions[0][1]
            
        except Exception as e:
            self.logger.error(f"Error finding compatible version for {package_name}: {e}")
            return None
    
    def clear_cache(self):
        """Clear the internal package cache"""
        self._package_cache = {}