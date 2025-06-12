"""Schema retrieval and caching utility for Hatch schemas.

This module provides utilities for:
1. Discovering latest schema versions via GitHub API
2. Downloading schemas directly from GitHub releases
3. Caching schemas locally for offline use
4. Validating schema updates and version management
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Import the separated classes
from .schema_fetcher import SchemaFetcher, SCHEMA_TYPES
from .schema_cache import SchemaCache, CACHE_DIR

# Configure logging
logger = logging.getLogger("hatch.schema_retriever")

class SchemaRetriever:
    """Main class for retrieving and managing schemas."""
    
    def __init__(self, cache_dir: Path = None):
        """Initialize the schema retriever.
        
        Args:
            cache_dir (Path, optional): Custom path to store cached schemas. If None, use default. Defaults to None.
        """
        self.cache = SchemaCache(cache_dir or CACHE_DIR)
        self.fetcher = SchemaFetcher()
    
    def get_schema(self, schema_type: str, version: str = "latest", force_update: bool = False) -> Optional[Dict[str, Any]]:
        """Get a schema, either from cache or by downloading.
        
        This is the main method for obtaining schema data. It first tries to get the schema from the cache,
        and if not available or if updates are forced, it attempts to download it.
        
        Args:
            schema_type (str): Type of schema ("package" or "registry")
            version (str, optional): Version of schema or "latest". Defaults to "latest".
            force_update (bool, optional): If True, force check for updates regardless of cache status. Defaults to False.
            
        Returns:
            Optional[Dict[str, Any]]: Schema as a dictionary or None if not available
        """
        # Validate schema type
        if schema_type not in SCHEMA_TYPES:
            logger.error(f"Unknown schema type: {schema_type}")
            return None
          # For "latest", try to update cache if needed and return the cached version
        if version == "latest":
            if force_update or not self.cache.is_fresh() or not self.cache.has_schema(schema_type):
                self.update_schemas(force=force_update)
            
            # First try to get the latest version number
            latest_version = self.cache.get_latest_version(schema_type)
            
            # Try to load the schema from the version-specific folder first,
            # fallback to the main folder if not found
            schema = self.cache.load_schema(schema_type, latest_version)
            if schema:
                return schema
            return self.cache.load_schema(schema_type)
          # For specific version, first check if it's already in the cache
        normalized_version = version if version.startswith('v') else f"v{version}"
        if not force_update and self.cache.has_schema(schema_type, normalized_version):
            return self.cache.load_schema(schema_type, normalized_version)
            
        # If not in cache or force update, download it directly
        schema_data = self.fetcher.download_specific_version(schema_type, version)
        if schema_data:
            # Cache the specific version in its own folder
            self.cache.save_schema(schema_type, schema_data, normalized_version)
            return schema_data
            
        logger.error(f"Could not retrieve {schema_type} schema version {version}")
        return None
    
    def update_schemas(self, force: bool = False) -> bool:
        """Check for schema updates and download if needed.
        
        Args:
            force (bool, optional): If True, force update regardless of cache freshness. Defaults to False.
            
        Returns:
            bool: True if any schema was updated, False otherwise
        """
        # Skip update if cache is fresh and not forcing
        if not force and self.cache.is_fresh():
            logger.debug("Cache is fresh, skipping update")
            return False
            
        # Get latest releases from GitHub
        releases = self.fetcher.get_releases()
        if not releases:
            logger.warning("Could not retrieve GitHub releases")
            return False
            
        # Extract schema information from releases
        schema_info = self.fetcher.extract_schema_info(releases)
        if not schema_info:
            logger.warning("No schema information found in releases")
            return False
            
        updated = False
        
        # Process each schema type
        for schema_type in SCHEMA_TYPES:
            if schema_type not in schema_info:
                continue
                
            # Get schema URL
            schema_url = schema_info.get(schema_type, {}).get("url")
            if not schema_url:
                continue
            
            # Download schema
            schema_data = self.fetcher.download_schema(schema_url)
            if not schema_data:
                continue
            
            # Get the version
            version = schema_info.get(f"latest_{schema_type}_version")
            
            # Save to cache - both in the version-specific folder and main folder
            if version:
                # Save to version-specific folder
                self.cache.save_schema(schema_type, schema_data, version)
                
                # Also save to main folder (no version) for backward compatibility
                if self.cache.save_schema(schema_type, schema_data):
                    updated = True
                    logger.info(f"Updated {schema_type} schema to version {version}")
        
        # Update cache info if any schema was updated
        if updated:
            self.cache.update_info(schema_info)
            
        return updated


# Create a default instance for easier imports
schema_retriever = SchemaRetriever()


def get_package_schema(version: str = "latest", force_update: bool = False) -> Optional[Dict[str, Any]]:
    """Helper function to get the package schema.
    
    Args:
        version (str, optional): Version of the schema, or "latest". Defaults to "latest".
        force_update (bool, optional): If True, force a check for updates. Defaults to False.
        
    Returns:
        Optional[Dict[str, Any]]: The package schema as a dictionary, or None if not available
    """
    return schema_retriever.get_schema("package", version, force_update)


def get_registry_schema(version: str = "latest", force_update: bool = False) -> Optional[Dict[str, Any]]:
    """Helper function to get the registry schema.
    
    Args:
        version (str, optional): Version of the schema, or "latest". Defaults to "latest".
        force_update (bool, optional): If True, force a check for updates. Defaults to False.
        
    Returns:
        Optional[Dict[str, Any]]: The registry schema as a dictionary, or None if not available
    """
    return schema_retriever.get_schema("registry", version, force_update)


# If run as script, perform a test
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    # Test functionality
    print("Testing schema retriever...")
    
    # Force update of schemas
    updated = schema_retriever.update_schemas(force=True)
    print(f"Schema update forced: {'Updated' if updated else 'No update needed'}")
    
    # Load schemas
    pkg_schema = get_package_schema()
    reg_schema = get_registry_schema()
    
    print(f"Package schema loaded: {'Yes' if pkg_schema else 'No'}")
    if pkg_schema:
        print(f"Package schema title: {pkg_schema.get('title')}")
        
    print(f"Registry schema loaded: {'Yes' if reg_schema else 'No'}")
    if reg_schema:
        print(f"Registry schema title: {reg_schema.get('title')}")
