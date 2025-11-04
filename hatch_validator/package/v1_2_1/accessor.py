"""Package metadata accessor for schema version 1.2.1.

This module provides the metadata accessor for schema version 1.2.1,
which handles dual entry point configuration while delegating unchanged
concerns to the v1.2.0 accessor.
"""

import logging
from hatch_validator.core.pkg_accessor_base import HatchPkgAccessor as HatchPkgAccessorBase

logger = logging.getLogger("hatch.package.v1_2_1.accessor")

class HatchPkgAccessor(HatchPkgAccessorBase):
    """Metadata accessor for Hatch package schema version 1.2.1.
    
    Adapts access to metadata fields for the v1.2.1 schema structure,
    specifically handling dual entry point configuration while delegating
    unchanged concerns to the v1.2.0 accessor.
    """
    
    def can_handle(self, schema_version: str) -> bool:
        """Check if this accessor can handle schema version 1.2.1.
        
        Args:
            schema_version (str): Schema version to check
            
        Returns:
            bool: True if schema_version is '1.2.1'
        """
        return schema_version == "1.2.1"
    
    def get_entry_point(self, metadata):
        """Get the full entry point dict for v1.2.1.

        In v1.2.1, entry_point is a dict with mcp_server and hatch_mcp_server keys.
        This method returns the full dict to maintain backward compatibility with
        code that expects to access both entry points.

        Args:
            metadata (dict): Package metadata

        Returns:
            dict: Dual entry point dict with mcp_server and hatch_mcp_server keys
        """
        return metadata.get('entry_point', {})

    def get_mcp_entry_point(self, metadata):
        """Get MCP entry point from metadata.

        Args:
            metadata (dict): Package metadata

        Returns:
            str: MCP entry point value (e.g., "mcp_server.py")
        """
        entry_point = metadata.get('entry_point', {})
        return entry_point.get('mcp_server') if isinstance(entry_point, dict) else None

    def get_hatch_mcp_entry_point(self, metadata):
        """Get Hatch MCP entry point from metadata.

        Args:
            metadata (dict): Package metadata

        Returns:
            Any: Hatch MCP entry point value
        """
        return metadata.get('entry_point').get('hatch_mcp_server')
