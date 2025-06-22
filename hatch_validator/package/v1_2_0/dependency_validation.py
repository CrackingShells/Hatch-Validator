"""Dependency validation strategy for schema version v1.2.0.

This module implements dependency validation for the unified dependencies
structure introduced in v1.2.0, using the same validation logic as v1.1.0
but adapted for the new schema structure.
"""

import json
import logging
from typing import Dict, List, Tuple, Optional, Set
from pathlib import Path

from hatch_validator.core.validation_strategy import DependencyValidationStrategy, ValidationError
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.utils.hatch_dependency_graph import HatchDependencyGraphBuilder
from hatch_validator.utils.version_utils import VersionConstraintValidator
from hatch_validator.registry.registry_service import RegistryService, RegistryError
from hatch_validator.package.package_service import PackageService

logger = logging.getLogger("hatch.dependency_validation_v1_2_0")
logger.setLevel(logging.DEBUG)


class DependencyValidation(DependencyValidationStrategy):
    """Strategy for validating dependencies according to v1.2.0 schema using utility modules.
    
    This implementation uses the same validation logic as v1.1.0 but adapted for
    the unified dependencies structure in v1.2.0:
    - dependencies.hatch: Array of Hatch package dependencies
    - dependencies.python: Array of Python package dependencies (format validation only)
    - dependencies.system: Array of System package dependencies (format validation only)
    - dependencies.docker: Array of Docker image dependencies (format validation only)
    """
    def __init__(self):
        """Initialize the dependency validation strategy."""
        self.version_validator = VersionConstraintValidator()
        self.registry_service : Optional[RegistryService] = None

    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate dependencies according to v1.2.0 schema using utility modules.
        
        In v1.2.0, dependencies are stored in a unified object:
        - dependencies.hatch: Array of Hatch package dependencies
        - dependencies.python: Array of Python package dependencies
        - dependencies.system: Array of System package dependencies  
        - dependencies.docker: Array of Docker image dependencies
        
        Args:
            metadata (Dict): Package metadata containing dependency information
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether dependency validation was successful
                - List[str]: List of dependency validation errors
        """
        try:
            # Initialize package service from the context if available
            package_service = context.get_data("package_service", None)
            if package_service is None:
                # Create a package service with the provided metadata
                package_service = PackageService(metadata)

            # Store package service for use in helper methods
            self.package_service = package_service

            # Initialize registry service from the context if available
            # Get registry data from context
            registry_data = context.registry_data
            registry_service = context.get_data("registry_service", None)
            
            # Check if registry data is missing
            if registry_data is None:
                logger.error("No registry data available for dependency validation")
                raise ValidationError("No registry data available for dependency validation")
            
            if registry_service is None:
                # Create a registry service with the provided data
                registry_service = RegistryService(registry_data)
            
            # Store registry service for use in helper methods
            self.registry_service = registry_service

            errors = []
            is_valid = True
            # Get dependencies from v1.2.0 unified format
            dependencies = package_service.get_dependencies()
            hatch_dependencies = dependencies.get('hatch', [])

            # Validate Hatch dependencies
            if hatch_dependencies:
                hatch_valid, hatch_errors = self._validate_hatch_dependencies(
                    hatch_dependencies, context
                )
                if not hatch_valid:
                    errors.extend(hatch_errors)
                    is_valid = False

        except Exception as e:
            logger.error(f"Error during dependency validation: {e}")
            errors.append(f"Error during dependency validation: {e}")
            is_valid = False
        
        logger.debug(f"Dependency validation result: {is_valid}, errors: {errors}")

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
            hatch_dep_graph_builder = HatchDependencyGraphBuilder(
                package_service=self.package_service,
                registry_service=self.registry_service
            )
            dependency_graph = hatch_dep_graph_builder.build_dependency_graph(hatch_dependencies, context)
            logger.debug(f"Dependency graph: {json.dumps(dependency_graph.to_dict(), indent=2)}")

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

    def _parse_hatch_dep_name(self, dep_name: str) -> Tuple[Optional[str], str]:
        """Parse a hatch dependency name into (repo, package_name).

        This is only used when it has already been determined that the dependency is remote.
        Otherwise, absolute paths on windows may contain colons, which would be misinterpreted as a repo prefix.

        Args:
            dep_name (str): Dependency name, possibly with repo prefix.
        Returns:
            Tuple[Optional[str], str]: (repo_name, package_name). repo_name is None if not present.
        """
        if ':' in dep_name:
            repo, pkg = dep_name.split(':', 1)
            return repo, pkg
        return None, dep_name
    
    def _validate_single_hatch_dependency(self, dep: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate a single Hatch dependency.

        Args:
            dep (Dict): Dependency definition
            context (ValidationContext): Validation context
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        errors = []
        is_valid = True
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
        
        # Check if this looks like a local path, otherwise treat as remote
        if self.package_service.is_local_dependency(dep, context.package_dir):
            # Local dependency - check if allowed
            if not context.allow_local_dependencies:
                errors.append(f"Local dependency '{dep_name}' not allowed in this context")
                return False, errors
            local_valid, local_errors = self._validate_local_dependency(dep, context)
            if not local_valid:
                errors.extend(local_errors)
                is_valid = False
        else:
            # Remote dependency - validate through registry
            registry_valid, registry_errors = self._validate_registry_dependency(dep, context)
            if not registry_valid:
                errors.extend(registry_errors)
                is_valid = False
        
        return is_valid, errors
    
    def _validate_local_dependency(self, dep: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate a local file dependency.

        Args:
            dep (Dict): Local dependency definition
            context (ValidationContext): Validation context
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        errors = []
        dep_name = dep.get('name')
        
        # Resolve path
        path = Path(dep_name)
        if context.package_dir and not path.is_absolute():
            path = context.package_dir / path
        
        # Check if path exists as a file (not a directory)
        if path.exists():
            if not path.is_dir():
                errors.append(f"Local dependency '{dep_name}' path is not a directory: {path}")
                return False, errors
        else:
            errors.append(f"Local dependency '{dep_name}' path is not a directory: {path}")
            return False, errors
        
        # Check for metadata file
        metadata_path = path / "hatch_metadata.json"
        if not metadata_path.exists():
            errors.append(f"Local dependency '{dep_name}' missing hatch_metadata.json: {metadata_path}")
            return False, errors
        
        return True, []
    
    def _validate_registry_dependency(self, dep: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate a registry dependency.

        Args:
            dep (Dict): Registry dependency definition
            context (ValidationContext): Validation context
        Returns:
            Tuple[bool, List[str]]: Validation result and errors
        """
        errors = []
        dep_name = dep.get('name')
        version_constraint = dep.get('version_constraint')
        
        # Parse repo and package name
        repo, pkg = self._parse_hatch_dep_name(dep_name)
        
        if repo:
            # Check repo existence
            if not self.registry_service.repository_exists(repo):
                errors.append(f"Repository '{repo}' not found in registry for dependency '{dep_name}'")
                return False, errors
            # Check package existence in repo
            if not self.registry_service.package_exists(pkg, repo_name=repo):
                errors.append(f"Package '{pkg}' not found in repository '{repo}' for dependency '{dep_name}'")
                return False, errors
        else:
            # No repo prefix, check package in any repo
            if not self.registry_service.package_exists(pkg):
                errors.append(f"Registry dependency '{pkg}' not found in registry for dependency '{dep_name}'")
                return False, errors
        
        # Check version compatibility if constraint is specified
        if version_constraint:
            version_compatible, version_error = self.registry_service.validate_version_compatibility(
                dep_name, version_constraint)
            if not version_compatible:
                errors.append(f"No version of '{dep_name}' satisfies constraint {version_constraint}: {version_error}")
                return False, errors
        
        return True, []
