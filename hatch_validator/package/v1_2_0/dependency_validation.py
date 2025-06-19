"""Dependency validation strategy for schema version v1.2.0.

This module implements dependency validation for the unified dependencies
structure introduced in v1.2.0, focusing on Hatch package dependencies
and dependency graph validation.
"""

import logging
from typing import Dict, List, Tuple, Optional

from hatch_validator.core.validation_strategy import DependencyValidationStrategy
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.utils.dependency_graph import DependencyGraph
from hatch_validator.utils.version_utils import VersionConstraintValidator
from hatch_validator.registry.registry_service import RegistryService

logger = logging.getLogger("hatch.dependency_validation_v1_2_0")


class DependencyValidation(DependencyValidationStrategy):
    """Strategy for validating dependencies according to v1.2.0 schema.
    
    In v1.2.0, dependencies are unified under a single 'dependencies' object.
    This strategy focuses on Hatch package dependencies validation since
    schema validation handles format validation for other dependency types.
    """
    
    def __init__(self):
        """Initialize the dependency validation strategy."""
        self.version_validator = VersionConstraintValidator()
    
    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate dependencies according to v1.2.0 schema structure.
        
        This focuses on Hatch package dependencies validation including:
        - Package existence in registry
        - Version constraint validation
        - Dependency graph cycle detection
        
        Format validation for python, system, and docker dependencies
        is handled by schema validation.
        
        Args:
            metadata (Dict): Package metadata containing dependency information
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether dependency validation was successful
                - List[str]: List of dependency validation errors
        """
        # Initialize registry service from the context if available
        # Get registry data from context
        registry_data = context.registry_data
        registry_service = context.get_data("registry_service", None)
        
        # Check if registry data is missing
        if registry_data is None:
            logger.error("No registry data available for dependency validation")
            return False, ["No registry data available for dependency validation"]
        
        if registry_service is None:
            # Create a registry service with the provided data
            registry_service = RegistryService(registry_data)
        
        all_errors = []
        is_valid = True
        
        # Get the unified dependencies object
        dependencies = metadata.get("dependencies", {})
        
        if not dependencies:
            logger.info("No dependencies found - validation passed")
            return True, []
        
        # Focus only on Hatch dependencies for detailed validation
        hatch_deps = dependencies.get("hatch", [])
        if hatch_deps:
            valid, errors = self._validate_hatch_dependencies(hatch_deps, registry_service)
            if not valid:
                is_valid = False
                all_errors.extend(errors)
            
            # Validate Hatch dependency graph for cycles
            graph_valid, graph_errors = self._validate_hatch_dependency_graph(hatch_deps, registry_service)
            if not graph_valid:
                is_valid = False
                all_errors.extend(graph_errors)
        
        if is_valid:
            logger.info("Hatch dependency validation passed for v1.2.0")
        
        return is_valid, all_errors    
    def _validate_hatch_dependencies(self, hatch_deps: List[Dict], 
                                     registry_service: RegistryService) -> Tuple[bool, List[str]]:
        """Validate Hatch package dependencies.
        
        Args:
            hatch_deps (List[Dict]): List of Hatch dependencies
            registry_service (RegistryService): Registry service for lookups
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        errors = []
        is_valid = True
        
        for i, dep in enumerate(hatch_deps):
            dep_name = dep.get("name", f"<unnamed_hatch_dep_{i}>")
            
            # Validate version constraint format
            version_constraint = dep.get("version_constraint")
            if version_constraint:
                if not self.version_validator.is_valid_constraint(version_constraint):
                    errors.append(f"Invalid version constraint '{version_constraint}' for Hatch dependency '{dep_name}'")
                    is_valid = False
            
            # Check if package exists in registry
            if not registry_service.package_exists(dep_name):
                errors.append(f"Hatch package '{dep_name}' not found in registry")
                is_valid = False
                continue
            
            # Validate version constraint against available versions
            if version_constraint:
                available_versions = registry_service.get_package_versions(dep_name)
                if available_versions:
                    matching_versions = self.version_validator.filter_versions_by_constraint(
                        available_versions, version_constraint
                    )
                    if not matching_versions:
                        errors.append(f"No versions of Hatch package '{dep_name}' satisfy constraint '{version_constraint}'")
                        is_valid = False
        
        return is_valid, errors
    
    def _validate_hatch_dependency_graph(self, hatch_deps: List[Dict], 
                                         registry_service: RegistryService) -> Tuple[bool, List[str]]:
        """Validate Hatch dependency graph for cycles.
        
        Args:
            hatch_deps (List[Dict]): List of Hatch dependencies
            registry_service (RegistryService): Registry service for dependency lookup
            
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        try:
            dependency_graph = DependencyGraph()
            
            # Build the dependency graph
            for dep in hatch_deps:
                dep_name = dep.get("name")
                if dep_name:
                    dependency_graph.add_dependency("current_package", dep_name)
                    
                    # Get transitive dependencies from registry
                    dep_metadata = registry_service.get_package_metadata(dep_name)
                    if dep_metadata:
                        dep_dependencies = dep_metadata.get("dependencies", {}).get("hatch", [])
                        for transitive_dep in dep_dependencies:
                            transitive_name = transitive_dep.get("name")
                            if transitive_name:
                                dependency_graph.add_dependency(dep_name, transitive_name)
            
            # Check for cycles
            cycles = dependency_graph.find_cycles()
            if cycles:
                cycle_descriptions = [" -> ".join(cycle) for cycle in cycles]
                return False, [f"Circular dependency detected: {cycle}" for cycle in cycle_descriptions]
            
            return True, []
        
        except Exception as e:
            logger.error(f"Error validating dependency graph: {e}")
            return False, [f"Error validating dependency graph: {str(e)}"]
