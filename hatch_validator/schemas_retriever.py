#!/usr/bin/env python
"""Schema retrieval and caching utility for Hatch schemas.

This module provides utilities for:
1. Discovering latest schema versions via GitHub API
2. Downloading schemas directly from GitHub releases
3. Caching schemas locally for offline use
4. Validating schema updates and version management
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

import requests

# Configure logging
logger = logging.getLogger("hatch.schema_retriever")

# Configuration
GITHUB_API_BASE = "https://api.github.com/repos/crackingshells/Hatch-Schemas"
GITHUB_RELEASES_BASE = "https://github.com/crackingshells/Hatch-Schemas/releases/download"
CACHE_DIR = Path.home() / ".hatch" / "schemas"
DEFAULT_CACHE_TTL = 86400  # 24 hours in seconds
DEFAULT_VERSION = "v1.2.0"  # Fallback if no version can be determined

# Schema type definitions
SCHEMA_TYPES = {
    "package": {
        "filename": "hatch_pkg_metadata_schema.json",
        "tag_prefix": "schemas-package-",
    },
    "registry": {
        "filename": "hatch_all_pkg_metadata_schema.json",
        "tag_prefix": "schemas-registry-",
    }
}


class SchemaFetcher:
    """Handles network operations to retrieve schemas from GitHub."""
    
    def __init__(self, api_base: str = GITHUB_API_BASE, releases_base: str = GITHUB_RELEASES_BASE):
        """Initialize the schema fetcher.
        
        Args:
            api_base (str, optional): Base URL for GitHub API requests. Defaults to GITHUB_API_BASE.
            releases_base (str, optional): Base URL for GitHub release downloads. Defaults to GITHUB_RELEASES_BASE.
        """
        self.api_base = api_base
        self.releases_base = releases_base
    
    def get_releases(self) -> list:
        """Fetch GitHub releases information.
        
        Returns:
            list: List containing release data or empty list if fetch fails
        """
        try:
            logger.debug(f"Requesting releases from {self.api_base}/releases")
            response = requests.get(f"{self.api_base}/releases", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching releases: {e}")
            return []
    
    def extract_schema_info(self, releases: list) -> Dict[str, Any]:
        """Process GitHub releases data to extract schema information.
        
        Args:
            releases (list): List of release data from GitHub API
            
        Returns:
            Dict[str, Any]: Dictionary with extracted schema information
        """
        info = {
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        for release in releases:
            tag = release.get('tag_name', '')
            
            for schema_type, config in SCHEMA_TYPES.items():
                prefix = config['tag_prefix']
                version_key = f"latest_{schema_type}_version"
                
                # Only process the first (latest) release for each type
                if tag.startswith(prefix) and version_key not in info:
                    version = tag.replace(prefix, '')
                    info[version_key] = version
                    info[schema_type] = {
                        'version': version,
                        'url': f"{self.releases_base}/{tag}/{config['filename']}",
                        'release_url': release.get('html_url', '')
                    }
        
        return info
    
    def download_schema(self, url: str) -> Optional[Dict[str, Any]]:
        """Download a schema JSON file from URL.
        
        Args:
            url (str): URL to download the schema from
            
        Returns:
            Optional[Dict[str, Any]]: Schema as a dictionary or None if download fails
        """
        try:
            logger.info(f"Downloading schema from {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            logger.error(f"Error downloading schema: {e}")
            return None
    
    def download_specific_version(self, schema_type: str, version: str) -> Optional[Dict[str, Any]]:
        """Download a specific schema version directly.
        
        Args:
            schema_type (str): Type of schema ("package" or "registry")
            version (str): Version to download, should include 'v' prefix
            
        Returns:
            Optional[Dict[str, Any]]: Schema as a dictionary or None if download fails
        """
        if schema_type not in SCHEMA_TYPES:
            logger.error(f"Unknown schema type: {schema_type}")
            return None
            
        # Ensure version has 'v' prefix
        if not version.startswith('v'):
            version = f"v{version}"
            
        config = SCHEMA_TYPES[schema_type]
        tag = f"{config['tag_prefix']}{version}"
        url = f"{self.releases_base}/{tag}/{config['filename']}"
        
        logger.info(f"Downloading {schema_type} schema version {version} from {url}")
        return self.download_schema(url)


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
