
import logging
from typing import Optional
from pathlib import Path

from hatch_validator.core.pkg_accessor_base import HatchPkgAccessor as HatchPkgAccessorBase

logger = logging.getLogger("hatch.package.v1_2_0.accessor")
logger.setLevel(logging.DEBUG)

class HatchPkgAccessor(HatchPkgAccessorBase):
    """Metadata accessor for Hatch package schema version 1.2.0.

    Adapts access to metadata fields for the v1.2.0 schema structure.
    """
    def can_handle(self, schema_version: str) -> bool:
        """Check if this accessor can handle schema version 1.2.0.

        Args:
            schema_version (str): Schema version to check
        Returns:
            bool: True if schema_version is '1.2.0'
        """
        return schema_version == "1.2.0"

    def get_dependencies(self, metadata):
        """Get dependencies from metadata for v1.2.0.

        Args:
            metadata (dict): Package metadata
        Returns:
            dict: Dict with 'hatch', 'python', 'system', and 'docker' keys for dependencies
        """
        deps = metadata.get('dependencies', {})
        return {
            'hatch': deps.get('hatch', []),
            'python': deps.get('python', []),
            'system': deps.get('system', []),
            'docker': deps.get('docker', [])
        }

    def is_local_dependency(self, dep, root_dir : Optional[Path] = None):
        """Check if a Hatch dependency is local for v1.2.0.

        Args:
            dep (dict): Dependency dict
            root_dir (Path, optional): Root directory of the package
        Returns:
            bool: Always False for v1.2.0 (no 'type' field)
        """
        try:
            # Attempt to convert the name to a Path object
            name_as_path = Path(dep.get('name', ''))
        except ValueError:
            # If conversion fails, it's not a valid path
            return False

        if not name_as_path.is_absolute():
            if root_dir:
                # If root_dir is provided, resolve relative paths against it
                name_as_path = root_dir / name_as_path
            name_as_path = name_as_path.resolve()

        logger.debug(f"Checking if dependency '{name_as_path}' is local")

        # Check if the path is a directory (not a file)
        return name_as_path.exists()
