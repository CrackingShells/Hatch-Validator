"""Dependency validation strategy for schema version v1.1.0.

This module implements dependency validation using the decoupled utility modules
for graph operations, version constraints, and registry interactions.
"""

import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from hatch_validator.core.validation_strategy import DependencyValidationStrategy
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.utils.dependency_graph import DependencyGraph, DependencyGraphError
from hatch_validator.utils.version_utils import VersionConstraintValidator, VersionConstraintError
from hatch_validator.utils.registry_client import RegistryManager, LocalFileRegistryClient, RegistryError

logger = logging.getLogger("hatch.dependency_validation_v1_1_0")


class DependencyValidationV1_1_0(DependencyValidationStrategy):
    """Strategy for validating dependencies according to v1.1.0 schema using utility modules.
    
    This implementation uses the decoupled utility modules for:
    - Graph operations (cycle detection, topological sorting)
    - Version constraint validation
    - Registry interactions
    """
    
    def __init__(self):
        """Initialize the dependency validation strategy."""
        self.version_validator = VersionConstraintValidator()
        self.registry_manager = None
    
    def _get_registry_manager(self, context: ValidationContext) -> Optional[RegistryManager]:
        """Get or create registry manager instance.
        
        Args:
            context (ValidationContext): Validation context with registry data
            
        Returns:
            Optional[RegistryManager]: Configured registry manager instance, or None if no registry
        """
        if self.registry_manager is None and context.registry_data:
            # Create a mock registry client with the context data
            # In a real implementation, this could be more sophisticated
            from hatch_validator.utils.registry_client import RegistryClient
            
            class MockRegistryClient(RegistryClient):
                def __init__(self, registry_data):
                    self.registry_data = registry_data
                    self._loaded = True
                
                def load_registry_data(self) -> bool:
                    return True
                
                def get_package_info(self, package_name: str):
                    packages = self.registry_data.get('packages', {})
                    if package_name in packages:
                        package_data = packages[package_name]
                        versions = []
                        if 'versions' in package_data:
                            versions = list(package_data['versions'].keys())
                        elif 'version' in package_data:
                            versions = [package_data['version']]
                        
                        from hatch_validator.utils.registry_client import PackageInfo
                        return PackageInfo(package_name, versions, package_data)
                    return None
                
                def package_exists(self, package_name: str) -> bool:
                    packages = self.registry_data.get('packages', {})
                    return package_name in packages
                
                def get_all_packages(self) -> List[str]:
                    packages = self.registry_data.get('packages', {})
                    return list(packages.keys())
                
                def is_loaded(self) -> bool:
                    return self._loaded
            
            mock_client = MockRegistryClient(context.registry_data)
            self.registry_manager = RegistryManager(mock_client)
        
        return self.registry_manager
    
    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate dependencies according to v1.1.0 schema using utility modules.
        
        In v1.1.0, dependencies are stored in separate arrays:
        - hatch_dependencies: Array of Hatch package dependencies
        - python_dependencies: Array of Python package dependencies
        
        Args:
            metadata (Dict): Package metadata containing dependency information
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether dependency validation was successful
                - List[str]: List of dependency validation errors
        """
        errors = []
        is_valid = True
        
        # Get dependencies from v1.1.0 format
        hatch_dependencies = metadata.get('hatch_dependencies', [])
        python_dependencies = metadata.get('python_dependencies', [])
        
        logger.debug(f"Validating v1.1.0 dependencies - Hatch: {len(hatch_dependencies)}, Python: {len(python_dependencies)}")
        
        # Early check for local dependencies if they're not allowed
        if not context.allow_local_dependencies:
            local_deps = [dep for dep in hatch_dependencies 
                         if dep.get('type', {}).get('type') == 'local']
            if local_deps:
                for dep in local_deps:
                    logger.error(f"Local dependency '{dep.get('name')}' not allowed in this context")
                    errors.append(f"Local dependency '{dep.get('name')}' not allowed in this context")
                is_valid = False
                return is_valid, errors
        
        # Validate Hatch dependencies
        if hatch_dependencies:
            hatch_valid, hatch_errors = self._validate_hatch_dependencies(
                hatch_dependencies, context
            )
            if not hatch_valid:
                errors.extend(hatch_errors)
                is_valid = False
        
        # Validate Python dependencies format
        if python_dependencies:
            python_valid, python_errors = self._validate_python_dependencies(
                python_dependencies
            )
            if not python_valid:
                errors.extend(python_errors)
                is_valid = False
        
        return is_valid, errors
    
    def _validate_hatch_dependencies(self, hatch_dependencies: List[Dict], 
                                   context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate Hatch package dependencies.
        
        Args:
            hatch_dependencies (List[Dict]): List of Hatch dependency definitions
            context (ValidationContext): Validation context
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        errors = []
        is_valid = True
        
        # Step 1: Validate individual dependencies
        for dep in hatch_dependencies:
            dep_valid, dep_errors = self._validate_single_hatch_dependency(dep, context)
            if not dep_valid:
                errors.extend(dep_errors)
                is_valid = False
        
        # Step 2: Build dependency graph and check for cycles
        try:
            dependency_graph = self._build_dependency_graph(hatch_dependencies, context)
            has_cycles, cycles = dependency_graph.detect_cycles()
            
            if has_cycles:
                for cycle in cycles:
                    cycle_str = " -> ".join(cycle)
                    error_msg = f"Circular dependency detected: {cycle_str}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                is_valid = False
        except Exception as e:
            logger.error(f"Error building dependency graph: {e}")
            errors.append(f"Error analyzing dependency graph: {e}")
            is_valid = False
        
        return is_valid, errors
    
    def _validate_single_hatch_dependency(self, dep: Dict, 
                                        context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate a single Hatch dependency.
        
        Args:
            dep (Dict): Dependency definition
            context (ValidationContext): Validation context
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        errors = []
        is_valid = True
        
        # Validate required fields
        dep_name = dep.get('name')
        if not dep_name:
            errors.append("Hatch dependency missing name")
            return False, errors
        
        # Validate version constraint if present
        version_constraint = dep.get('version_constraint')
        if version_constraint:
            constraint_valid, constraint_error = self.version_validator.validate_constraint(version_constraint)
            if not constraint_valid:
                errors.append(f"Invalid version constraint for '{dep_name}': {constraint_error}")
                is_valid = False
        
        # Validate dependency type
        dep_type = dep.get('type', {})
        type_name = dep_type.get('type')
        
        if type_name == 'local':
            local_valid, local_errors = self._validate_local_dependency(dep, context)
            if not local_valid:
                errors.extend(local_errors)
                is_valid = False
        elif type_name == 'registry' or type_name is None:  # Default to registry
            registry_valid, registry_errors = self._validate_registry_dependency(dep, context)
            if not registry_valid:
                errors.extend(registry_errors)
                is_valid = False
        else:
            errors.append(f"Unknown dependency type for '{dep_name}': {type_name}")
            is_valid = False
        
        return is_valid, errors
    
    def _validate_local_dependency(self, dep: Dict, 
                                 context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate a local file dependency.
        
        Args:
            dep (Dict): Local dependency definition
            context (ValidationContext): Validation context
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        errors = []
        is_valid = True
        
        dep_name = dep.get('name')
        dep_type = dep.get('type', {})
        uri = dep_type.get('uri')
        
        # Validate URI
        if not uri:
            errors.append(f"Local dependency '{dep_name}' missing URI")
            return False, errors
        
        if not uri.startswith('file://'):
            errors.append(f"Local dependency '{dep_name}' URI must start with 'file://'")
            is_valid = False
        else:
            # Extract and validate path
            path_str = uri[7:]  # Remove "file://"
            path = Path(path_str)
            
            # Resolve relative paths
            if context.package_dir and not path.is_absolute():
                path = context.package_dir / path
            
            # Check if path exists
            if not path.exists() or not path.is_dir():
                errors.append(f"Local dependency '{dep_name}' path does not exist: {path}")
                is_valid = False
            else:
                # Check for metadata file
                metadata_path = path / "hatch_metadata.json"
                if not metadata_path.exists():
                    errors.append(f"Local dependency '{dep_name}' missing hatch_metadata.json: {metadata_path}")
                    is_valid = False
        
        return is_valid, errors
    
    def _validate_registry_dependency(self, dep: Dict, 
                                    context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate a registry dependency.
        
        Args:
            dep (Dict): Registry dependency definition
            context (ValidationContext): Validation context
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        errors = []
        is_valid = True
        
        dep_name = dep.get('name')
        version_constraint = dep.get('version_constraint')
        
        # Get registry manager
        registry_manager = self._get_registry_manager(context)
        if not registry_manager:
            # If no registry data, we can't validate registry dependencies
            logger.warning(f"No registry data available to validate dependency '{dep_name}'")
            return True, []  # Don't fail validation if no registry available
        
        # Check if package exists in registry
        exists, error = registry_manager.validate_package_exists(dep_name)
        if not exists:
            errors.append(f"Registry dependency '{dep_name}' not found: {error}")
            is_valid = False
        elif version_constraint:
            # If package exists and has version constraint, validate it
            # For now, we just validate the constraint format since we already did package existence
            # In a more sophisticated implementation, we could validate specific versions
            pass
        
        return is_valid, errors
    
    def _build_dependency_graph(self, hatch_dependencies: List[Dict], 
                              context: ValidationContext) -> DependencyGraph:
        """Build a dependency graph from Hatch dependencies.
        
        Args:
            hatch_dependencies (List[Dict]): List of Hatch dependency definitions
            context (ValidationContext): Validation context
            
        Returns:
            DependencyGraph: Constructed dependency graph
        """
        graph = DependencyGraph()
        
        # Get the current package name if available
        current_package = context.get_data("current_package_name", "current_package")
        
        # Add current package to graph
        graph.add_package(current_package)
        
        # Add dependencies
        for dep in hatch_dependencies:
            dep_name = dep.get('name')
            if dep_name:
                graph.add_dependency(current_package, dep_name)
                
                # For local dependencies, recursively add their dependencies
                dep_type = dep.get('type', {})
                if dep_type.get('type') == 'local':
                    self._add_local_dependency_graph(dep, graph, context)
        
        return graph
    
    def _add_local_dependency_graph(self, dep: Dict, graph: DependencyGraph, 
                                   context: ValidationContext) -> None:
        """Add local dependency and its transitive dependencies to the graph.
        
        Args:
            dep (Dict): Local dependency definition
            graph (DependencyGraph): Graph to add dependencies to
            context (ValidationContext): Validation context
        """
        dep_name = dep.get('name')
        dep_type = dep.get('type', {})
        uri = dep_type.get('uri')
        
        if not uri or not uri.startswith('file://'):
            return
        
        # Extract path
        path_str = uri[7:]  # Remove "file://"
        path = Path(path_str)
        
        # Resolve relative paths
        if context.package_dir and not path.is_absolute():
            path = context.package_dir / path
        
        # Load metadata if available
        metadata_path = path / "hatch_metadata.json"
        if metadata_path.exists():
            try:
                import json
                with open(metadata_path, 'r') as f:
                    local_metadata = json.load(f)
                
                # Add transitive dependencies
                local_hatch_deps = local_metadata.get('hatch_dependencies', [])
                for local_dep in local_hatch_deps:
                    local_dep_name = local_dep.get('name')
                    if local_dep_name:
                        graph.add_dependency(dep_name, local_dep_name)
                        
                        # Recursively add if it's also local
                        local_dep_type = local_dep.get('type', {})
                        if local_dep_type.get('type') == 'local':
                            self._add_local_dependency_graph(local_dep, graph, context)
                            
            except Exception as e:
                logger.warning(f"Could not load metadata for local dependency '{dep_name}': {e}")
    
    def _validate_python_dependencies(self, python_dependencies: List[Dict]) -> Tuple[bool, List[str]]:
        """Validate Python package dependencies format.
        
        Args:
            python_dependencies (List[Dict]): List of Python dependency definitions
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        errors = []
        is_valid = True
        
        for dep in python_dependencies:
            dep_name = dep.get('name')
            if not dep_name:
                errors.append("Python dependency missing name")
                is_valid = False
                continue
            
            version_constraint = dep.get('version_constraint')
            if version_constraint:
                constraint_valid, constraint_error = self.version_validator.validate_constraint(version_constraint)
                if not constraint_valid:
                    errors.append(f"Invalid version constraint for Python dependency '{dep_name}': {constraint_error}")
                    is_valid = False
        
        return is_valid, errors
