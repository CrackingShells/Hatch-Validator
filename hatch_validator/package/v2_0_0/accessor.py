"""Package metadata accessor for schema version 2.0.0.

This module provides the metadata accessor for schema version 2.0.0.
Schema version 2.0.0 introduces the new hatch_schema_version field,
uses an authors array instead of a singular author object, and renames
`tools[].description` to `tools[].desc`.
"""

import logging
from typing import Any, Dict

from hatch_validator.core.pkg_accessor_base import (
    HatchPkgAccessor as HatchPkgAccessorBase,
)

logger = logging.getLogger("hatch.package.v2_0_0.accessor")


class HatchPkgAccessor(HatchPkgAccessorBase):
    """Metadata accessor for Hatch package schema version 2.0.0."""

    def can_handle(self, schema_version: str) -> bool:
        """Check if this accessor can handle schema version 2.0.0.

        Args:
            schema_version (str): Schema version to check

        Returns:
            bool: True if schema_version is '2.0.0'
        """
        return schema_version == "2.0.0"

    def get_package_schema_version(self, metadata: Dict[str, Any]) -> Any:
        """Get the package schema version value from metadata.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Schema version value from either hatch_schema_version or package_schema_version
        """
        return metadata.get("hatch_schema_version") or metadata.get(
            "package_schema_version"
        )

    def get_author(self, metadata: Dict[str, Any]) -> Any:
        """Get authors from metadata.

        Schema v2.0.0 stores author information in an array under the `authors` key.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Author information, preferably the authors list or legacy author object
        """
        authors = metadata.get("authors")
        if isinstance(authors, list):
            return authors
        if authors is not None:
            return [authors]
        return metadata.get("author")

    def get_tools(self, metadata: Dict[str, Any]) -> Any:
        """Get tools from metadata.

        Tools entries in schema v2.0.0 use `desc` instead of `description`.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Tools list from metadata
        """
        return metadata.get("tools", [])

    def get_provenance(self, metadata: Dict[str, Any]) -> Any:
        """Get provenance metadata for v2.0.0.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Provenance metadata object or None if not present
        """
        return metadata.get("provenance")

    def get_citations(self, metadata: Dict[str, Any]) -> Any:
        """Get citations metadata for v2.0.0.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Citations list or an empty list if not present
        """
        return metadata.get("citations", [])
