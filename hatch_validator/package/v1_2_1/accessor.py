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
        """Get entry point from metadata for v1.2.1.
        
        Returns the dual entry point object containing both FastMCP server
        and HatchMCP wrapper file paths.
        
        Args:
            metadata (dict): Package metadata
            
        Returns:
            dict: Dual entry point object with keys:
                - 'mcp_server': FastMCP server file path
                - 'hatch_mcp_server': HatchMCP wrapper file path
                
        Example:
            {
                "mcp_server": "mcp_arithmetic.py",
                "hatch_mcp_server": "hatch_mcp_arithmetic.py"
            }
        """
        entry_point = metadata.get('entry_point')
        logger.debug(f"Retrieved dual entry point: {entry_point}")
        return entry_point
