"""Legacy dependency validation implementation for v1.1.0.

This module contains the old dependency validation implementation that is kept
for comparison testing purposes only. It should not be used in production code.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple

from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.core.validation_strategy import DependencyValidationStrategy
from .dependency_resolver import DependencyResolver, DependencyResolutionError


# Configure logging
logger = logging.getLogger("hatch.legacy_dependency_validation_v1_1_0")
logger.setLevel(logging.INFO)


class LegacyDependencyValidation(DependencyValidationStrategy):
    """Legacy strategy for validating dependencies according to v1.1.0 schema.
    
    This class is kept for comparison testing purposes only and should not
    be used in production code. Use DependencyValidationV1_1_0 instead.
    """
    
    def __init__(self):
        """Initialize the legacy dependency validation strategy."""
        self.dependency_resolver = None
    
    def _get_dependency_resolver(self, context: ValidationContext) -> DependencyResolver:
        """Get or create dependency resolver instance.
        
        Args:
            context (ValidationContext): Validation context with registry data
            
        Returns:
            DependencyResolver: Configured dependency resolver instance
        """
        if self.dependency_resolver is None:
            self.dependency_resolver = DependencyResolver(context.registry_data)
        return self.dependency_resolver
    
    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate dependencies according to v1.1.0 schema using legacy implementation.
        
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
        
        # Get pending update information for circular dependency detection
        pending_update = context.get_data("pending_update")
        
        # Use the dependency resolver for validation
        if hatch_dependencies:
            resolver = self._get_dependency_resolver(context)
            # Validate dependencies
            validation_valid, validation_errors = resolver.validate_dependencies(
                hatch_dependencies,
                context.package_dir
            )
            
            if not validation_valid:
                errors.extend(validation_errors)
                is_valid = False
                
            # Detect circular dependencies
            has_cycles, cycles = resolver.detect_dependency_cycles(
                hatch_dependencies,
                context.package_dir,
                pending_update
            )
            
            if has_cycles:
                for cycle in cycles:
                    cycle_str = " -> ".join(cycle)
                    error_msg = f"Circular dependency detected: {cycle_str}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                is_valid = False
        
        # Validate Python dependencies format
        for dep in python_dependencies:
            dep_name = dep.get('name')
            if not dep_name:
                errors.append("Python dependency missing name")
                is_valid = False
                continue
                
            version_constraint = dep.get('version_constraint')
            if version_constraint:
                resolver = self._get_dependency_resolver(context)
                constraint_valid, constraint_error = resolver.validate_version_constraint(
                    dep_name, version_constraint
                )
                if not constraint_valid:
                    errors.append(constraint_error)
                    is_valid = False
        
        return is_valid, errors
