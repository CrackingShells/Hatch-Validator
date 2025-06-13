"""Dependency validation strategy for schema version v1.1.0.

This module implements dependency validation using the decoupled utility modules
for graph operations, version constraints, and registry interactions.
"""

import logging
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from hatch_validator.core.validation_strategy import DependencyValidationStrategy
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.utils.dependency_graph import DependencyGraph
from hatch_validator.utils.version_utils import VersionConstraintValidator
from hatch_validator.utils.registry_client import RegistryManager

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
        self.registry_manager = RegistryManager().get_instance()
    
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
        elif type_name == 'remote' or type_name is None:  # Default to registry
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
        
        # Check if package exists in registry
        exists, error = self.registry_manager.validate_package_exists(dep_name)
        if not exists:
            errors.append(f"Registry dependency '{dep_name}' not found: {error}")
            is_valid = False
        elif version_constraint:
            # Check if the available version satisfies the constraint
            version_compatible, version_error = self.registry_manager.validate_version_compatibility(
                dep_name, version_constraint            )
            if not version_compatible:
                errors.append(f"No version of '{dep_name}' satisfies constraint {version_constraint}: {version_error}")
                is_valid = False
        
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
