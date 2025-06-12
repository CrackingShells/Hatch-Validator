"""Schema caching utility for managing local schema storage.

This module provides functionality for:
1. Caching schemas locally for offline use
2. Managing schema versioning and updates
3. Retrieving cached schema data
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logger = logging.getLogger("hatch.schema_cache")

# Configuration
CACHE_DIR = Path.home() / ".hatch" / "schemas"
DEFAULT_CACHE_TTL = 86400  # 24 hours in seconds
DEFAULT_VERSION = "v1.2.0"  # Fallback if no version can be determined

# Import schema types from schema_fetcher
from .schema_fetcher import SCHEMA_TYPES


class SchemaCache:
    """Manages local schema file storage and retrieval."""
    
    def __init__(self, cache_dir: Path = CACHE_DIR):
        """Initialize the schema cache.
        
        Args:
            cache_dir (Path, optional): Directory to store cached schemas. Defaults to CACHE_DIR.
        """
        self.cache_dir = cache_dir
        self.info_file = cache_dir / "schema_info.json"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_info(self) -> Dict[str, Any]:
        """Get cached schema information.
        
        Returns:
            Dict[str, Any]: Dictionary with schema info or empty dict if not available
        """
        if not self.info_file.exists():
            return {}
            
        try:
            with open(self.info_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading cache info: {e}")
            return {}
    
    def update_info(self, info: Dict[str, Any]) -> bool:
        """Update the cached schema information.
        
        Args:
            info (Dict[str, Any]): Schema information to cache
            
        Returns:
            bool: True if update succeeded, False otherwise
        """
        try:
            with open(self.info_file, "w") as f:
                json.dump(info, f, indent=2)
            return True
        except IOError as e:
            logger.error(f"Error writing cache info: {e}")
            return False
    
    def is_fresh(self, max_age: int = DEFAULT_CACHE_TTL) -> bool:
        """Check if the cache is still fresh.
        
        Args:
            max_age (int, optional): Maximum age in seconds for the cache to be considered fresh. Defaults to DEFAULT_CACHE_TTL.
            
        Returns:
            bool: True if cache is fresh, False otherwise
        """
        info = self.get_info()
        if not info or "updated_at" not in info:
            return False
            
        try:
            updated_str = info["updated_at"].replace("Z", "+00:00")
            updated = datetime.fromisoformat(updated_str)
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
                
            now = datetime.now(timezone.utc)
            age = (now - updated).total_seconds()
            
            return age < max_age
        except (ValueError, TypeError):
            return False
    
    def get_schema_path(self, schema_type: str, version: str = None) -> Path:
        """Get the path where a schema should be stored.
        
        Args:
            schema_type (str): Type of schema ("package" or "registry")
            version (str, optional): Schema version. If provided, schema will be stored in a version-specific folder. Defaults to None.
            
        Returns:
            Path: Path object for the schema file
            
        Raises:
            ValueError: If the schema type is unknown
        """
        if schema_type not in SCHEMA_TYPES:
            raise ValueError(f"Unknown schema type: {schema_type}")

        # Base directory for this schema type
        base_dir = self.cache_dir / schema_type
        
        if version:
            # Normalize version format (ensure v prefix)
            if not version.startswith('v'):
                version = f"v{version}"
                
            # Store in version-specific subfolder
            schema_dir = base_dir / version
        else:
            # No version specified, use the main schema directory
            schema_dir = base_dir
            
        schema_dir.mkdir(parents=True, exist_ok=True)
        return schema_dir / SCHEMA_TYPES[schema_type]["filename"]
    
    def has_schema(self, schema_type: str, version: str = None) -> bool:
        """Check if a schema exists in the cache.
        
        Args:
            schema_type (str): Type of schema ("package" or "registry")
            version (str, optional): Schema version to check. If None, checks for the default schema. Defaults to None.
            
        Returns:
            bool: True if schema exists in cache, False otherwise
        """
        try:
            path = self.get_schema_path(schema_type, version)
            return path.exists() and path.stat().st_size > 0
        except ValueError:
            return False
    
    def load_schema(self, schema_type: str, version: str = None) -> Optional[Dict[str, Any]]:
        """Load a schema from the cache.
        
        Args:
            schema_type (str): Type of schema ("package" or "registry")
            version (str, optional): Schema version to load. If None, loads the default schema. Defaults to None.
            
        Returns:
            Optional[Dict[str, Any]]: Schema as a dictionary or None if not available
        """
        try:
            path = self.get_schema_path(schema_type, version)
            if not path.exists():
                return None
                
            with open(path, "r") as f:
                logger.info(f"Loading cached schema {schema_type} version {version} from {path}")
                return json.load(f)
        except (ValueError, json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading cached schema: {e}")
            return None
    
    def save_schema(self, schema_type: str, schema: Dict[str, Any], version: str = None) -> bool:
        """Save a schema to the cache.
        
        Args:
            schema_type (str): Type of schema ("package" or "registry")
            schema (Dict[str, Any]): Schema data to save
            version (str, optional): Schema version. If provided, schema will be stored in a version-specific folder. Defaults to None.
            
        Returns:
            bool: True if save succeeded, False otherwise
        """
        try:
            path = self.get_schema_path(schema_type, version)
            with open(path, "w") as f:
                json.dump(schema, f, indent=2)
            return True
        except (ValueError, IOError) as e:
            logger.error(f"Error saving schema to cache: {e}")
            return False
    
    def get_latest_version(self, schema_type: str) -> str:
        """Get the latest known version of a schema type.
        
        Args:
            schema_type (str): Type of schema ("package" or "registry")
            
        Returns:
            str: Latest version string with 'v' prefix or default version if not found
        """
        info = self.get_info()
        version = info.get(f"latest_{schema_type}_version")
        
        # Ensure version has 'v' prefix
        if version and not version.startswith('v'):
            version = f"v{version}"
            
        return version if version else DEFAULT_VERSION
