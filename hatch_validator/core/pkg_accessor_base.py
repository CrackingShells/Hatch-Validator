"""Base metadata accessor class for Chain of Responsibility pattern.

This module provides the abstract base class for metadata accessors that
adapt access to package metadata dictionaries according to the schema version.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path

class HatchPkgAccessor(ABC):
    """Abstract base class for metadata accessors in the Chain of Responsibility pattern.
    
    Each accessor in the chain can either handle the access for a specific
    schema version or pass the request to the next accessor in the chain. The base class
    provides default delegation methods for each specific metadata concern,
    allowing concrete accessors to override only the concerns that have changed in their version.
    """
    def __init__(self, next_accessor: Optional['HatchPkgAccessor'] = None):
        """Initialize the accessor with an optional next accessor in the chain.
        
        Args:
            next_accessor (HatchPkgAccessor, optional): Next accessor in the chain. Defaults to None.
        """
        self.next_accessor = next_accessor

    @abstractmethod
    def can_handle(self, schema_version: str) -> bool:
        """Determine if this accessor can handle the given schema version.
        
        Args:
            schema_version (str): Schema version to check
        
        Returns:
            bool: True if this accessor can handle the schema version
        """
        pass

    def set_next(self, accessor: 'HatchPkgAccessor') -> 'HatchPkgAccessor':
        """Set the next accessor in the chain.
        
        Args:
            accessor (HatchPkgAccessor): Next accessor to set

        Returns:
            HatchPkgAccessor: The accessor that was set as next
        """
        self.next_accessor = accessor
        return accessor

    def get_dependencies(self, metadata: Dict[str, Any]) -> Any:
        """Get dependencies from metadata.
        
        Default behavior: delegate to next accessor in chain if available.
        
        Args:
            metadata (Dict[str, Any]): Package metadata
        
        Returns:
            Any: Dependencies structure
        
        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_dependencies(metadata)
        raise NotImplementedError("Dependency accessor not implemented for this schema version")

    def is_local_dependency(self, metadata: Dict[str, Any], root_dir: Optional[Path] = None) -> bool:
        """Check if a Hatch dependency is local.

        Default behavior: delegate to next accessor in chain if available.

        Args:
            metadata (Dict[str, Any]): Package metadata
            root_dir (Path, optional): Root directory of the package
        Returns:
            bool: True if the dependency is local, False otherwise
        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.is_local_dependency(metadata, root_dir)
        raise NotImplementedError("Local dependency accessor not implemented for this schema version")

    def get_entry_point(self, metadata: Dict[str, Any]) -> Any:
        """Get entry point from metadata.
        
        Default behavior: delegate to next accessor in chain if available.
        
        Args:
            metadata (Dict[str, Any]): Package metadata
        
        Returns:
            Any: Entry point value
        
        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_entry_point(metadata)
        raise NotImplementedError("Entry point accessor not implemented for this schema version")

    def get_mcp_entry_point(self, metadata: Dict[str, Any]) -> Any:
        """Get MCP entry point from metadata.

        Default behavior: delegate to next accessor in chain if available.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: MCP entry point value

        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_mcp_entry_point(metadata)
        raise NotImplementedError("MCP entry point accessor not implemented for this schema version"
                                  )

    def get_hatch_mcp_entry_point(self, metadata: Dict[str, Any]) -> Any:
        """Get Hatch MCP entry point from metadata.

        Default behavior: delegate to next accessor in chain if available.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Hatch MCP entry point value

        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_hatch_mcp_entry_point(metadata)
        raise NotImplementedError("Hatch MCP entry point accessor not implemented for this schema version")

    def get_tools(self, metadata: Dict[str, Any]) -> Any:
        """Get tools from metadata.
        
        Default behavior: delegate to next accessor in chain if available.
        
        Args:
            metadata (Dict[str, Any]): Package metadata
        
        Returns:
            Any: Tools structure
        
        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_tools(metadata)
        raise NotImplementedError("Tools accessor not implemented for this schema version")

    def get_package_schema_version(self, metadata: Dict[str, Any]) -> Any:
        """Get package schema version from metadata.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Package schema version value

        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_package_schema_version(metadata)
        raise NotImplementedError("Package schema version accessor not implemented for this schema version")

    def get_name(self, metadata: Dict[str, Any]) -> Any:
        """Get package name from metadata.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Package name value

        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_name(metadata)
        raise NotImplementedError("Name accessor not implemented for this schema version")

    def get_version(self, metadata: Dict[str, Any]) -> Any:
        """Get package version from metadata.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Package version value

        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_version(metadata)
        raise NotImplementedError("Version accessor not implemented for this schema version")

    def get_description(self, metadata: Dict[str, Any]) -> Any:
        """Get package description from metadata.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Package description value

        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_description(metadata)
        raise NotImplementedError("Description accessor not implemented for this schema version")

    def get_tags(self, metadata: Dict[str, Any]) -> Any:
        """Get tags from metadata.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Tags value

        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_tags(metadata)
        raise NotImplementedError("Tags accessor not implemented for this schema version")

    def get_author(self, metadata: Dict[str, Any]) -> Any:
        """Get author from metadata.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Author value

        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_author(metadata)
        raise NotImplementedError("Author accessor not implemented for this schema version")

    def get_contributors(self, metadata: Dict[str, Any]) -> Any:
        """Get contributors from metadata.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Contributors value

        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_contributors(metadata)
        raise NotImplementedError("Contributors accessor not implemented for this schema version")

    def get_license(self, metadata: Dict[str, Any]) -> Any:
        """Get license from metadata.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: License value

        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_license(metadata)
        raise NotImplementedError("License accessor not implemented for this schema version")

    def get_repository(self, metadata: Dict[str, Any]) -> Any:
        """Get repository from metadata.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Repository value

        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_repository(metadata)
        raise NotImplementedError("Repository accessor not implemented for this schema version")

    def get_documentation(self, metadata: Dict[str, Any]) -> Any:
        """Get documentation from metadata.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Documentation value

        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_documentation(metadata)
        raise NotImplementedError("Documentation accessor not implemented for this schema version")

    def get_compatibility(self, metadata: Dict[str, Any]) -> Any:
        """Get compatibility from metadata.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Compatibility value

        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_compatibility(metadata)
        raise NotImplementedError("Compatibility accessor not implemented for this schema version")

    def get_citations(self, metadata: Dict[str, Any]) -> Any:
        """Get citations from metadata.

        Args:
            metadata (Dict[str, Any]): Package metadata

        Returns:
            Any: Citations value

        Raises:
            NotImplementedError: If there is no next accessor and this method is not overridden
        """
        if self.next_accessor:
            return self.next_accessor.get_citations(metadata)
        raise NotImplementedError("Citations accessor not implemented for this schema version")
