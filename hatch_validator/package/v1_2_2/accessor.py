"""Package metadata accessor for schema version 1.2.2.

This module provides the metadata accessor for schema version 1.2.2,
which introduces conda package manager support for Python dependencies.
All metadata access patterns remain unchanged from v1.2.1, except for
the new channel field in Python dependencies.
"""

import logging
from typing import Dict, Any
from hatch_validator.core.pkg_accessor_base import HatchPkgAccessor as HatchPkgAccessorBase

logger = logging.getLogger("hatch.package.v1_2_2.accessor")

class HatchPkgAccessor(HatchPkgAccessorBase):
    """Metadata accessor for Hatch package schema version 1.2.2.

    Schema version 1.2.2 introduces conda package manager support for Python
    dependencies with optional channel specification. This accessor implements
    the channel accessor while delegating all other operations to v1.2.1.
    """

    def can_handle(self, schema_version: str) -> bool:
        """Check if this accessor can handle schema version 1.2.2.

        Args:
            schema_version (str): Schema version to check

        Returns:
            bool: True if schema_version is '1.2.2'
        """
        return schema_version == "1.2.2"

    def get_python_dependency_channel(self, dependency: Dict[str, Any]) -> Any:
        """Get channel from a Python dependency.

        This method retrieves the channel field from a Python dependency,
        which is available in schema version 1.2.2 for conda packages.

        Args:
            dependency (Dict[str, Any]): Python dependency object

        Returns:
            Any: Channel value (e.g., "conda-forge", "bioconda"), or None if not specified
        """
        return dependency.get('channel')

