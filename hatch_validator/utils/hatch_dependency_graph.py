"""Utilities for building Hatch dependency graphs across schema versions.

This module provides a unified interface for building a complete dependency graph for Hatch packages,
parameterized by a dependency extractor function that handles schema-specific differences.
"""

import json
import logging
from typing import Dict, List, Optional, Set
from pathlib import Path

from hatch_validator.utils.dependency_graph import DependencyGraph
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.core.validation_strategy import ValidationError
from hatch_validator.registry.registry_service import RegistryService, RegistryError
from hatch_validator.package.package_service import PackageService

logger = logging.getLogger("hatch.hatch_dependency_graph")
logger.setLevel(logging.DEBUG)

class HatchDependencyGraphBuilder:
    """Builder for creating a Hatch dependency graph."""

    def __init__(self, package_service: PackageService, registry_service: RegistryService):
        """Initialize the dependency graph builder.

        Args:
            package_service (PackageService): Service for package operations.
            registry_service (RegistryService, optional): Service for registry operations. Defaults to None.
        """
        self.package_service = package_service
        self.registry_service = registry_service

    def _get_local_dep_pkg_metadata(self, dep: Dict, root_dir: Optional[Path] = None) -> Dict:
        """Get the metadata for a local dependency.

        This method retrieves the package metadata from the local dependency's metadata file.

        Args:
            dep (Dict): Local dependency definition
            root_dir (Path, optional): Root directory of the package

        Returns:
            Dict: Metadata of the local dependency
        """
        path = self._get_local_dependency_path(dep, root_dir)
        metadata_path = path / "hatch_metadata.json"

        if not metadata_path.exists():
            logger.error(f"Local dependency metadata file does not exist: {metadata_path}")
            raise ValidationError(f"Local dependency metadata file does not exist: {metadata_path}")
        
        with open(metadata_path, 'r') as f:
            local_metadata = json.load(f)

        return local_metadata

    def build_dependency_graph(self, hatch_dependencies: List[Dict], context: ValidationContext) -> 'DependencyGraph':
        """Build a dependency graph from Hatch dependencies.

        This method builds a complete dependency graph including all transitive dependencies
        for both local and remote packages.

        Args:
            hatch_dependencies (List[Dict]): List of Hatch dependency definitions
            context (ValidationContext): Validation context

        Returns:
            DependencyGraph: Constructed dependency graph
        """
        graph = DependencyGraph()
        pkg_name, _ = context.get_data("pending_update", ("current_package", None))
        logger.debug(f"Building dependency graph for package: {pkg_name}")
        graph.add_package(pkg_name)
        
        processed = set()
        for dep in hatch_dependencies:
            if self.package_service.is_local_dependency(dep, context.package_dir):
                self._add_local_dependency_graph(pkg_name, dep, graph, context, context.package_dir)

            else:
                self._add_remote_dependency_graph(pkg_name, dep, graph, context, processed)
        return graph

    def get_install_ready_dependencies(self, context: ValidationContext) -> List[Dict]:
        """Get install-ready Hatch dependencies in topological order.
        
        This method builds the dependency graph and returns a list of dependency objects
        in the order they should be installed, with resolved versions.
        
        Args:
            context (ValidationContext): Validation context containing package information.
            
        Returns:
            List[Dict]: List of dependency objects with keys: name, version_constraint, resolved_version.
            
        Raises:
            ValidationError: If there are validation errors during graph construction.
            DependencyGraphError: If the dependency graph contains cycles.
        """
        graph = self.build_dependency_graph(self.package_service.get_dependencies(), context)
        return graph.get_install_order_dependencies()

    def _get_local_dependency_path(self, dep: Dict, root_dir: Optional[Path] = None) -> Path:
        """Get the local file path for a local dependency.

        Args:
            dep (Dict): Local dependency definition
            root_dir (Path, optional): Root directory of the package

        Returns:
            Path: Path to the local dependency
        """
        dep_name = dep.get('name')
        path = Path(dep_name)
        if not path.is_absolute():
            if root_dir:
                path = root_dir / path
            path = path.resolve()

        if not path.is_dir():
            logger.error(f"Local dependency path is not a directory: {path}")
            raise ValidationError(f"Local dependency path is not a directory: {path}")
        
        if not path.exists():
            logger.error(f"Local dependency path does not exist: {path}")
            raise ValidationError(f"Local dependency path does not exist: {path}")
        
        return path

    def _add_local_dependency_graph(self, parent_pkg_name: str, dep: Dict, graph: DependencyGraph, context: ValidationContext, root_dir: Optional[Path] = None):
        """Add local dependency and its transitive dependencies to the graph.

        Args:
            parent_pkg_name (str): Name of the parent package
            dep (Dict): Local dependency definition
            graph (DependencyGraph): Graph to add dependencies to
            context (ValidationContext): Validation context
            root_dir (Path): Root directory of the package depending on this local dependency
        """
        try:

            local_pkg_metadata = self._get_local_dep_pkg_metadata(dep, root_dir)
            local_pkg_service = PackageService(local_pkg_metadata)
            local_pkg_name = local_pkg_service.get_field('name')

            path = self._get_local_dependency_path(dep, root_dir)
            remote_dep_obj = {
                    "name": local_pkg_name,
                    "version_constraint": dep.get('version_constraint'),
                    "resolved_version": local_pkg_service.get_field('version'),  # For local deps, use actual version
                    "uri": f"file://{str(path)}"
                }
            graph.add_dependency(parent_pkg_name, remote_dep_obj)

            deps_obj = local_pkg_service.get_dependencies()
            hatch_deps = deps_obj.get('hatch', [])

            for dep in hatch_deps:
                if self.package_service.is_local_dependency(dep, path):
                    self._add_local_dependency_graph(local_pkg_name, dep, graph, context, path)
                else:
                    self._add_remote_dependency_graph(local_pkg_name, dep, graph, context)

        except Exception as e:
            logger.error(f"Could not load metadata for local dependency '{local_pkg_name}': {e}")
            raise ValidationError(f"Could not load metadata for local dependency '{local_pkg_name}': {e}")

    def _add_remote_dependency_graph(self, parent_pkg_name: str, dep: Dict, graph: DependencyGraph, context: ValidationContext, processed: Set[str] = None):
        """Add remote dependency and its transitive dependencies to the graph.

        This method uses the registry to fetch the complete dependency information
        for a remote package, handling the differential storage format.

        Args:
            parent_pkg_name (str): Name of the parent package
            dep (Dict): Remote dependency definition
            graph (DependencyGraph): Graph to add dependencies to
            context (ValidationContext): Validation context
            processed (Set[str], optional): Set of already processed dependencies to avoid cycles
        """
        if processed is None:
            processed = set()
        dep_name = dep.get('name')

        if not dep_name or dep_name in processed:
            return
        
        processed.add(dep_name)
        try:
            
            version_constraint = dep.get('version_constraint')
            compatible_version = self.registry_service.find_compatible_version(dep_name, version_constraint)

            # Create rich dependency object
            remote_dep_obj = {
                "name": dep_name,
                "version_constraint": version_constraint,
                "resolved_version": compatible_version,
                "uri": self.registry_service.get_package_uri(dep_name, compatible_version)
            }
            graph.add_dependency(parent_pkg_name, remote_dep_obj)

            hatch_deps_obj = self.registry_service.get_package_dependencies(dep_name, compatible_version)
            hatch_deps = hatch_deps_obj.get('dependencies', [])

            for remote_dep in hatch_deps:

                remote_dep_name = remote_dep.get('name')

                if remote_dep_name not in processed:
                    self._add_remote_dependency_graph(dep_name, remote_dep, graph, context, processed)

        except Exception as e:
            logger.error(f"Error processing remote dependency '{dep_name}': {e}")
            raise ValidationError(f"Error processing remote dependency '{dep_name}': {e}")

