"""Dependency validation strategy for schema version v2.0.0.

This module implements dependency validation for schema version 2.0.0.
Docker dependencies now require tag and digest instead of version_constraint,
and version_constraint is optional for all dependency types.
"""

import json
import logging
import re
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from hatch_validator.core.validation_strategy import DependencyValidationStrategy, ValidationError
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.utils.hatch_dependency_graph import HatchDependencyGraphBuilder
from hatch_validator.utils.version_utils import VersionConstraintValidator
from hatch_validator.registry.registry_service import RegistryService
from hatch_validator.package.package_service import PackageService

logger = logging.getLogger("hatch.dependency_validation_v2_0_0")
logger.setLevel(logging.DEBUG)


class DependencyValidation(DependencyValidationStrategy):
    """Strategy for validating dependencies according to v2.0.0 schema."""

    def __init__(self):
        """Initialize the dependency validation strategy."""
        self.version_validator = VersionConstraintValidator()
        self.registry_service: Optional[RegistryService] = None

    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate dependencies according to v2.0.0 schema.

        Args:
            metadata (Dict): Package metadata containing dependency information
            context (ValidationContext): Validation context with resources

        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether dependency validation was successful
                - List[str]: List of dependency validation errors
        """
        try:
            package_service = context.get_data("package_service", None)
            if package_service is None:
                package_service = PackageService(metadata)
            self.package_service = package_service

            registry_data = context.registry_data
            registry_service = context.get_data("registry_service", None)
            if registry_data is None:
                logger.error("No registry data available for dependency validation")
                raise ValidationError("No registry data available for dependency validation")
            if registry_service is None:
                registry_service = RegistryService(registry_data)
            self.registry_service = registry_service

            errors = []
            is_valid = True

            dependencies = package_service.get_dependencies()
            hatch_dependencies = dependencies.get('hatch', [])
            python_dependencies = dependencies.get('python', [])
            system_dependencies = dependencies.get('system', [])
            docker_dependencies = dependencies.get('docker', [])

            if hatch_dependencies:
                hatch_valid, hatch_errors = self._validate_hatch_dependencies(hatch_dependencies, context)
                if not hatch_valid:
                    errors.extend(hatch_errors)
                    is_valid = False

            if python_dependencies:
                python_valid, python_errors = self._validate_python_dependencies(python_dependencies, context)
                if not python_valid:
                    errors.extend(python_errors)
                    is_valid = False

            if system_dependencies:
                system_valid, system_errors = self._validate_system_dependencies(system_dependencies, context)
                if not system_valid:
                    errors.extend(system_errors)
                    is_valid = False

            if docker_dependencies:
                docker_valid, docker_errors = self._validate_docker_dependencies(docker_dependencies, context)
                if not docker_valid:
                    errors.extend(docker_errors)
                    is_valid = False

        except Exception as e:
            logger.error(f"Error during dependency validation: {e}")
            errors = [f"Error during dependency validation: {e}"]
            is_valid = False

        logger.debug(f"Dependency validation result: {is_valid}, errors: {errors}")
        return is_valid, errors

    def _validate_python_dependencies(self, python_dependencies: List[Dict],
                                      context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate Python package dependencies with optional version constraints."""
        errors = []
        is_valid = True

        for dep in python_dependencies:
            dep_valid, dep_errors = self._validate_single_python_dependency(dep, context)
            if not dep_valid:
                errors.extend(dep_errors)
                is_valid = False

        return is_valid, errors

    def _validate_single_python_dependency(self, dep: Dict,
                                           context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate a single Python dependency."""
        errors = []
        is_valid = True

        dep_name = dep.get('name')
        if not dep_name:
            errors.append("Python dependency missing name")
            return False, errors

        version_constraint = dep.get('version_constraint')
        if version_constraint:
            constraint_valid, constraint_error = self.version_validator.validate_constraint(version_constraint)
            if not constraint_valid:
                errors.append(f"Invalid version constraint for Python package '{dep_name}': {constraint_error}")
                is_valid = False

        package_manager = dep.get('package_manager', 'pip')
        if package_manager not in ['pip', 'conda']:
            errors.append(
                f"Invalid package_manager '{package_manager}' for Python package '{dep_name}'. Must be 'pip' or 'conda'"
            )
            is_valid = False

        channel = dep.get('channel')
        if channel is not None:
            if package_manager != 'conda':
                errors.append(
                    f"Channel '{channel}' specified for Python package '{dep_name}' with package_manager '{package_manager}'. Channel is only valid for conda packages"
                )
                is_valid = False
            else:
                channel_pattern = r'^[a-zA-Z0-9_\-]+$'
                if not re.match(channel_pattern, channel):
                    errors.append(
                        f"Invalid channel format '{channel}' for Python package '{dep_name}'. Must match pattern: {channel_pattern}"
                    )
                    is_valid = False

        return is_valid, errors

    def _validate_system_dependencies(self, system_dependencies: List[Dict],
                                      context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate system package dependencies."""
        errors = []
        is_valid = True

        for dep in system_dependencies:
            dep_valid, dep_errors = self._validate_single_system_dependency(dep, context)
            if not dep_valid:
                errors.extend(dep_errors)
                is_valid = False

        return is_valid, errors

    def _validate_single_system_dependency(self, dep: Dict,
                                           context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate a single system dependency."""
        errors = []
        is_valid = True

        dep_name = dep.get('name')
        if not dep_name:
            errors.append("System dependency missing name")
            return False, errors

        version_constraint = dep.get('version_constraint')
        if version_constraint:
            constraint_valid, constraint_error = self.version_validator.validate_constraint(version_constraint)
            if not constraint_valid:
                errors.append(f"Invalid version constraint for system package '{dep_name}': {constraint_error}")
                is_valid = False

        package_manager = dep.get('package_manager')
        if package_manager is not None and not isinstance(package_manager, str):
            errors.append(f"Invalid package_manager for system package '{dep_name}'. Must be a string")
            is_valid = False

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
        """Validate a single Docker dependency."""
        errors = []
        is_valid = True

        dep_name = dep.get('name')
        if not dep_name:
            errors.append("Docker dependency missing name")
            return False, errors

        tag = dep.get('tag')
        digest = dep.get('digest')
        if not digest:
            errors.append(f"Docker dependency '{dep_name}' missing required 'digest'")
            is_valid = False
        if tag is not None and not isinstance(tag, str):
            errors.append(f"Invalid Docker tag for '{dep_name}'. Must be a string")
            is_valid = False

        version_constraint = dep.get('version_constraint')
        if version_constraint is not None:
            errors.append(
                f"Docker dependency '{dep_name}' should use 'tag' and 'digest' instead of 'version_constraint'"
            )
            is_valid = False

        registry = dep.get('registry')
        if registry is not None and not isinstance(registry, str):
            errors.append(f"Invalid registry value for Docker dependency '{dep_name}'. Must be a string")
            is_valid = False

        if digest and isinstance(digest, str):
            digest_pattern = r'^[A-Za-z0-9_+.-]+:[A-Fa-f0-9]{32,}$'
            if not re.match(digest_pattern, digest):
                errors.append(
                    f"Invalid Docker digest '{digest}' for '{dep_name}'. Must match pattern '<algo>:<hex>'"
                )
                is_valid = False

        return is_valid, errors

    def _validate_hatch_dependencies(self, hatch_dependencies: List[Dict],
                                    context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate Hatch package dependencies."""
        errors = []
        is_valid = True

        for dep in hatch_dependencies:
            dep_valid, dep_errors = self._validate_single_hatch_dependency(dep, context)
            if not dep_valid:
                errors.extend(dep_errors)
                is_valid = False

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
                    errors.append(f"Circular dependency detected: {cycle_str}")
                is_valid = False
        except Exception as e:
            logger.error(f"Error building dependency graph: {e}")
            errors.append(f"Error analyzing dependency graph: {e}")
            is_valid = False

        return is_valid, errors

    def _parse_hatch_dep_name(self, dep_name: str) -> Tuple[Optional[str], str]:
        """Parse a hatch dependency name into (repo, package_name)."""
        if ':' in dep_name:
            repo, pkg = dep_name.split(':', 1)
            return repo, pkg
        return None, dep_name

    def _validate_single_hatch_dependency(self, dep: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate a single Hatch dependency."""
        errors = []
        is_valid = True

        dep_name = dep.get('name')
        if not dep_name:
            errors.append("Hatch dependency missing name")
            return False, errors

        version_constraint = dep.get('version_constraint')
        if version_constraint:
            constraint_valid, constraint_error = self.version_validator.validate_constraint(version_constraint)
            if not constraint_valid:
                errors.append(f"Invalid version constraint for '{dep_name}': {constraint_error}")
                is_valid = False

        if self.package_service.is_local_dependency(dep, context.package_dir):
            if not context.allow_local_dependencies:
                errors.append(f"Local dependency '{dep_name}' not allowed in this context")
                return False, errors
            local_valid, local_errors = self._validate_local_dependency(dep, context)
            if not local_valid:
                errors.extend(local_errors)
                is_valid = False
        else:
            registry_valid, registry_errors = self._validate_registry_dependency(dep, context)
            if not registry_valid:
                errors.extend(registry_errors)
                is_valid = False

        return is_valid, errors

    def _validate_local_dependency(self, dep: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate a local file dependency."""
        errors = []
        dep_name = dep.get('name')

        path = Path(dep_name)
        if context.package_dir and not path.is_absolute():
            path = context.package_dir / path

        if path.exists():
            if not path.is_dir():
                errors.append(f"Local dependency '{dep_name}' path is not a directory: {path}")
                return False, errors
        else:
            errors.append(f"Local dependency '{dep_name}' path is not a directory: {path}")
            return False, errors

        metadata_path = path / "hatch_metadata.json"
        if not metadata_path.exists():
            errors.append(f"Local dependency '{dep_name}' missing hatch_metadata.json: {metadata_path}")
            return False, errors

        return True, []

    def _validate_registry_dependency(self, dep: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate a registry dependency."""
        errors = []
        dep_name = dep.get('name')
        version_constraint = dep.get('version_constraint')

        repo, pkg = self._parse_hatch_dep_name(dep_name)

        if repo:
            if not self.registry_service.repository_exists(repo):
                errors.append(f"Repository '{repo}' not found in registry for dependency '{dep_name}'")
                return False, errors
            if not self.registry_service.package_exists(pkg, repo_name=repo):
                errors.append(f"Package '{pkg}' not found in repository '{repo}' for dependency '{dep_name}'")
                return False, errors
        else:
            if not self.registry_service.package_exists(pkg):
                errors.append(f"Registry dependency '{pkg}' not found in registry for dependency '{dep_name}'")
                return False, errors

        if version_constraint:
            version_compatible, version_error = self.registry_service.validate_version_compatibility(
                dep_name, version_constraint)
            if not version_compatible:
                errors.append(f"No version of '{dep_name}' satisfies constraint {version_constraint}: {version_error}")
                return False, errors

        return True, []
