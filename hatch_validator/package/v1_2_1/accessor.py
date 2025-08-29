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
        """From v1.2.1, returns the same as get_mcp_entry_point().

        Args:
            metadata (dict): Package metadata

        Returns:
            Any: Dual entry point value
        """
        return metadata.get('entry_point').get('mcp_server')
    
    def get_mcp_entry_point(self, metadata):
        """Get MCP entry point from metadata.

        Args:
            metadata (dict): Package metadata

        Returns:
            Any: MCP entry point value
        """
        return self.get_entry_point(metadata)

    def get_hatch_mcp_entry_point(self, metadata):
        """Get Hatch MCP entry point from metadata.

        Args:
            metadata (dict): Package metadata

        Returns:
            Any: Hatch MCP entry point value
        """
        return metadata.get('entry_point').get('hatch_mcp_server')
