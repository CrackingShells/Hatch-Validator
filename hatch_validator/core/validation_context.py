"""Validation context for carrying state between validator components.

This module provides the context object used to pass data and state between
validators and strategies in the validation chain.
"""

from pathlib import Path
from typing import Dict, Any, Optional


class ValidationContext:
    """Context object that carries validation state through the validator chain.
    
    This context provides a consistent interface for passing validation resources
    and state between validators and strategies in the chain.
    """
    
    def __init__(self, package_dir: Optional[Path] = None, registry_data: Optional[Dict] = None,
                 allow_local_dependencies: bool = True, force_schema_update: bool = False):
        """Initialize validation context.
        
        Args:
            package_dir (Path, optional): Path to the package being validated. Defaults to None.
            registry_data (Dict, optional): Registry data for dependency validation. Defaults to None.
            allow_local_dependencies (bool, optional): Whether local dependencies are allowed. Defaults to True.
            force_schema_update (bool, optional): Whether to force schema updates. Defaults to False.
        """
        self.package_dir = package_dir
        self.registry_data = registry_data
        self.allow_local_dependencies = allow_local_dependencies
        self.force_schema_update = force_schema_update
        self.additional_data = {}
    
    def set_data(self, key: str, value: Any) -> None:
        """Set additional data in the context.
        
        Args:
            key (str): Key for the data
            value (Any): Value to store
        """
        self.additional_data[key] = value
    
    def get_data(self, key: str, default: Any = None) -> Any:
        """Get additional data from the context.
        
        Args:
            key (str): Key for the data
            default (Any, optional): Default value if key not found. Defaults to None.
            
        Returns:
            Any: Value associated with the key or default
        """
        return self.additional_data.get(key, default)
