"""Dependency validation strategy for schema version v2.0.0.

This module implements dependency validation for schema version 2.0.0.
Only Docker-specific validation is owned here; Hatch, Python, and System
dependency validation is delegated to v1.2.2 via the chain.
"""

import logging
from typing import Dict, List, Tuple

from hatch_validator.core.validation_strategy import DependencyValidationStrategy
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.package.package_service import PackageService

logger = logging.getLogger("hatch.dependency_validation_v2_0_0")
logger.setLevel(logging.DEBUG)


class DependencyValidation(DependencyValidationStrategy):
    """Strategy for validating Docker dependencies according to v2.0.0 schema."""

    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate Docker dependencies according to v2.0.0 schema.

        Hatch, Python, and System dependency validation is handled by the
        previous validator in the chain. This strategy validates only the
        Docker subset, which requires a digest in v2.0.0.

        Args:
            metadata (Dict): Package metadata containing dependency information
            context (ValidationContext): Validation context with resources

        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether Docker dependency validation was successful
                - List[str]: List of Docker dependency validation errors
        """
        try:
            package_service = context.get_data("package_service", None)
            if package_service is None:
                package_service = PackageService(metadata)

            dependencies = package_service.get_dependencies()
            docker_dependencies = dependencies.get('docker', [])

            errors = []
            is_valid = True

            if docker_dependencies:
                docker_valid, docker_errors = self._validate_docker_dependencies(docker_dependencies, context)
                if not docker_valid:
                    errors.extend(docker_errors)
                    is_valid = False

        except Exception as e:
            logger.error(f"Error during Docker dependency validation: {e}")
            return False, [f"Error during Docker dependency validation: {e}"]

        logger.debug(f"Docker dependency validation result: {is_valid}, errors: {errors}")
        return is_valid, errors

    def _validate_docker_dependencies(self, docker_dependencies: List[Dict],
                                      context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate Docker image dependencies."""
        errors = []
        is_valid = True

        for dep in docker_dependencies:
            dep_valid, dep_errors = self._validate_single_docker_dependency(dep, context)
            if not dep_valid:
                errors.extend(dep_errors)
                is_valid = False

        return is_valid, errors

    def _validate_single_docker_dependency(self, dep: Dict,
                                           context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate a single Docker dependency.

        Structural checks (digest presence, digest pattern, version_constraint rejection)
        are enforced by the JSON schema and are not repeated here.
        """
        errors = []
        is_valid = True

        dep_name = dep.get('name')
        if not dep_name:
            errors.append("Docker dependency missing name")
            return False, errors

        tag = dep.get('tag')
        if tag is not None and not isinstance(tag, str):
            errors.append(f"Invalid Docker tag for '{dep_name}'. Must be a string")
            is_valid = False

        registry = dep.get('registry')
        if registry is not None and not isinstance(registry, str):
            errors.append(f"Invalid registry value for Docker dependency '{dep_name}'. Must be a string")
            is_valid = False

        return is_valid, errors
