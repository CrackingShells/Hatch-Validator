from pathlib import Path
from typing import Optional

from hatch_validator.core.pkg_accessor_base import HatchPkgAccessor as HatchPkgAccessorBase

class HatchPkgAccessor(HatchPkgAccessorBase):
    """Metadata accessor for Hatch package schema version 1.1.0.

    Adapts access to metadata fields for the v1.1.0 schema structure.
    """
    def can_handle(self, schema_version: str) -> bool:
        """Check if this accessor can handle schema version 1.1.0.

        Args:
            schema_version (str): Schema version to check
        Returns:
            bool: True if schema_version is '1.1.0'
        """
        return schema_version == "1.1.0"

    def get_dependencies(self, metadata):
        """Get dependencies from metadata for v1.1.0.

        Args:
            metadata (dict): Package metadata
        Returns:
            dict: Dict with 'hatch' and 'python' keys for dependencies
        """
        return {
            'hatch': metadata.get('hatch_dependencies', []),
            'python': metadata.get('python_dependencies', [])
        }

    def is_local_dependency(self, dep, root_dir: Optional[Path] = None):
        """Check if a Hatch dependency is local for v1.1.0.

        Args:
            dep (dict): Dependency dict
            root_dir (Path, optional): Root directory of the package
        Returns:
            bool: True if dependency type is 'local'
        """
        internal_type = dep.get('type')
        return internal_type.get('type') == 'local'

    def get_entry_point(self, metadata):
        return metadata.get('entry_point')

    def get_mcp_entry_point(self, metadata):
        """Until v1.2.1, MCP entry point is the same as the main entry point.
        Hence, this is equivalent to calling get_entry_point().

        Args:
            metadata (dict): Package metadata

        Returns:
            Any: MCP entry point value
        """
        return self.get_entry_point(metadata)

    def get_hatch_mcp_entry_point(self, metadata):
        """For v1.2.1, Hatch MCP entry point is the same as the main entry point.
        Hence, this is equivalent to calling get_entry_point().

        Args:
            metadata (dict): Package metadata

        Returns:
            Any: Hatch MCP entry point value
        """
        return self.get_entry_point(metadata)

    def get_tools(self, metadata):
        return metadata.get('tools', [])

    def get_package_schema_version(self, metadata):
        return metadata.get('package_schema_version')

    def get_name(self, metadata):
        return metadata.get('name')

    def get_version(self, metadata):
        return metadata.get('version')

    def get_description(self, metadata):
        return metadata.get('description')

    def get_tags(self, metadata):
        return metadata.get('tags', [])

    def get_author(self, metadata):
        return metadata.get('author')

    def get_contributors(self, metadata):
        return metadata.get('contributors', [])

    def get_license(self, metadata):
        return metadata.get('license')

    def get_repository(self, metadata):
        return metadata.get('repository')

    def get_documentation(self, metadata):
        return metadata.get('documentation')

    def get_compatibility(self, metadata):
        return metadata.get('compatibility', {})

    def get_citations(self, metadata):
        return metadata.get('citations', {})
