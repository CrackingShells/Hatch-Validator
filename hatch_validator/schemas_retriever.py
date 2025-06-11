#!/usr/bin/env python
"""Schema retrieval and caching utility for Hatch schemas.

This module provides utilities for:
1. Discovering latest schema versions via GitHub API
2. Downloading schemas directly from GitHub releases
3. Caching schemas locally for offline use
4. Validating schema updates and version management
"""

import os
import json
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

# Configure logging
logger = logging.getLogger("hatch.schema_retriever")
logger.setLevel(logging.INFO)

# Configuration
GITHUB_API_BASE = "https://api.github.com/repos/crackingshells/Hatch-Schemas"
GITHUB_RELEASES_BASE = "https://github.com/crackingshells/Hatch-Schemas/releases/download"
CACHE_DIR = Path.home() / ".hatch" / "schemas"
CACHE_INFO_FILE = CACHE_DIR / "schema_info.json"
DEFAULT_CACHE_DURATION = 86400  # 24 hours in seconds


class SchemaRetriever:
    def __init__(self, cache_dir: Path = None):
        """Initialize the schema retriever.
        
        Args:
            cache_dir: Custom path to store cached schemas. If None, use default.
        """
        self.cache_dir = cache_dir or CACHE_DIR
        self.cache_info_file = self.cache_dir / "schema_info.json"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cached_schema_info(self) -> Dict[str, Any]:
        """Get information about the locally cached schema versions."""
        if not self.cache_info_file.exists():
            logger.debug("No cached schema info found")
            return {}
        
        try:
            logger.debug(f"Reading cached schema info from {self.cache_info_file}")
            with open(self.cache_info_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading cached schema info: {e}")
            return {}

    def _update_cache_info(self, schema_info: Dict[str, Any]) -> bool:
        """Update the cached schema information."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Writing updated schema info to {self.cache_info_file}")
            with open(self.cache_info_file, "w") as f:
                json.dump(schema_info, f, indent=2)
            return True
        except IOError as e:
            logger.error(f"Error writing cache info: {e}")
            return False
    
    def _get_latest_schema_info(self) -> Dict[str, Any]:
        """Fetch information about the latest schema versions from the server."""
        try:
            logger.debug(f"Requesting releases from {GITHUB_API_BASE}/releases")
            response = requests.get(f"{GITHUB_API_BASE}/releases", timeout=10)
            response.raise_for_status()
            releases = response.json()
            
            # Extract latest versions for each schema type
            latest_schemas = {
                "updated_at": datetime.utcnow().isoformat() + "Z"
            }
            
            for release in releases:
                tag = release['tag_name']
                if tag.startswith('schemas-package-'):
                    if 'latest_package_version' not in latest_schemas:
                        version = tag.replace('schemas-package-', '')
                        latest_schemas['latest_package_version'] = version
                        latest_schemas['package'] = {
                            'version': version,
                            'url': f"{GITHUB_RELEASES_BASE}/schemas-package-{version}/hatch_pkg_metadata_schema.json",
                            'release_url': release['html_url']
                        }
                elif tag.startswith('schemas-registry-'):
                    if 'latest_registry_version' not in latest_schemas:
                        version = tag.replace('schemas-registry-', '')
                        latest_schemas['latest_registry_version'] = version
                        latest_schemas['registry'] = {
                            'version': version,
                            'url': f"{GITHUB_RELEASES_BASE}/schemas-registry-{version}/hatch_all_pkg_metadata_schema.json",
                            'release_url': release['html_url']
                        }
            
            logger.debug("Schema info retrieved successfully")
            return latest_schemas
        except requests.RequestException as e:
            logger.error(f"Error fetching schema info: {e}")
            return {}
    
    def _download_schema_file(self, schema_type: str, schema_url: str) -> bool:
        """Download a schema file directly from the raw URL.
        
        Args:
            schema_type: Either "package" or "registry".
            schema_url: Direct URL to the schema JSON file.
            
        Returns:
            bool: True if download was successful, False otherwise.
        """
        try:
            # Create schema type directory
            schema_cache_dir = self.cache_dir / schema_type
            schema_cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine filename based on schema type
            if schema_type == "package":
                filename = "hatch_pkg_metadata_schema.json"
            elif schema_type == "registry":
                filename = "hatch_all_pkg_metadata_schema.json"
            else:
                logger.error(f"Unknown schema type: {schema_type}")
                return False
            
            # Download the schema file
            logger.info(f"Downloading {schema_type} schema from {schema_url}")
            response = requests.get(schema_url, timeout=30)
            response.raise_for_status()
            
            # Save to cache
            schema_path = schema_cache_dir / filename
            with open(schema_path, "w") as f:
                json.dump(response.json(), f, indent=2)
            
            logger.debug(f"{schema_type.capitalize()} schema saved to {schema_path}")
            return True
        except Exception as e:
            logger.error(f"Error downloading {schema_type} schema: {e}")
            return False

    def check_and_update_schemas(self, force: bool = False) -> bool:
        """Check if new schema versions are available and update if needed.
        
        Args:
            force: If True, force an update even if the cache is recent
            
        Returns:
            bool: True if any schema was updated, False otherwise
        """
        # Get cached schema info
        cached_info = self._get_cached_schema_info()
        
        # Determine if we need to fetch new schema info
        need_to_fetch = force
        
        if not force and cached_info:
            try:
                cached_updated = datetime.fromisoformat(cached_info.get("updated_at", "1970-01-01T00:00:00+00:00").replace("Z", "+00:00"))
                if cached_updated.tzinfo is None:
                    cached_updated = cached_updated.replace(tzinfo=timezone.utc)
                now = datetime.now(timezone.utc)
                cache_age = (now - cached_updated).total_seconds()
                
                if cache_age < DEFAULT_CACHE_DURATION:
                    logger.debug(f"Cache is fresh (age: {cache_age:.0f}s < {DEFAULT_CACHE_DURATION}s)")
                    
                    # Verify that the schema files exist for each cached schema type
                    for schema_type in ["package", "registry"]:
                        if schema_type in cached_info:
                            schema_filename = self._get_schema_filename(schema_type)
                            schema_path = self.cache_dir / schema_type / schema_filename
                            
                            if not schema_path.exists():
                                logger.warning(f"Schema file {schema_path} referenced in cache doesn't exist.")
                                need_to_fetch = True
                                break
                else:
                    logger.debug(f"Cache is stale (age: {cache_age:.0f}s >= {DEFAULT_CACHE_DURATION}s)")
                    need_to_fetch = True
            except ValueError:
                logger.warning("Invalid timestamp in cached schema info")
                need_to_fetch = True
        else:
            need_to_fetch = True
        
        # If we don't need to fetch, return early - everything is up-to-date
        if not need_to_fetch:
            return False
        
        # Get latest schema info from server
        latest_info = self._get_latest_schema_info()
        if not latest_info:
            logger.warning("Could not retrieve latest schema information. Using cached version if available.")
            return False
        
        updated = False
        
        # Process each schema type
        for schema_type in ["package", "registry"]:
            # Skip if this schema type is not in the latest info
            if schema_type not in latest_info:
                logger.debug(f"No {schema_type} schema information in the latest info")
                continue
                
            latest_version_key = f"latest_{schema_type}_version"
            latest_version = latest_info.get(latest_version_key)
            
            # Skip if no latest version is defined
            if not latest_version:
                logger.debug(f"No latest version for {schema_type} schema")
                continue
            
            needs_update = True
            
            # Check if we have this version cached already
            if cached_info and schema_type in cached_info:
                cached_version_key = f"latest_{schema_type}_version"
                cached_version = cached_info.get(cached_version_key)
                
                if cached_version == latest_version:
                    # Check if the cached version is up to date
                    cached_updated = datetime.fromisoformat(cached_info.get("updated_at", "1970-01-01T00:00:00+00:00").replace("Z", "+00:00"))
                    if cached_updated.tzinfo is None:
                        cached_updated = cached_updated.replace(tzinfo=timezone.utc)
                    latest_updated = datetime.fromisoformat(latest_info.get("updated_at", "1970-01-01T00:00:00+00:00").replace("Z", "+00:00"))
                    if latest_updated.tzinfo is None:
                        latest_updated = latest_updated.replace(tzinfo=timezone.utc)
                    
                    if cached_updated >= latest_updated:
                        logger.info(f"{schema_type.capitalize()} schema is up to date (version {latest_version}).")
                        needs_update = False
            
            # Update schema if needed
            if needs_update:
                schema_url = latest_info.get(schema_type, {}).get("url")
                if schema_url:
                    logger.info(f"New {schema_type} schema version available: {latest_version}")
                    if self._download_schema_file(schema_type, schema_url):
                        updated = True
                        logger.info(f"{schema_type.capitalize()} schema updated successfully.")
                    else:
                        logger.error(f"{schema_type.capitalize()} schema update failed.")
                else:
                    logger.warning(f"No download URL found for {schema_type} schema")
        
        # Update cache info after all schemas are updated
        if updated:
            self._update_cache_info(latest_info)
        
        return updated
    def get_schema_path(self, schema_type: str, version: str = "latest") -> Optional[Path]:
        """Get the path to a schema file.
        
        Args:
            schema_type: Either "package" or "registry"
            version: Version of the schema, or "latest"
            
        Returns:
            Path to the schema file, or None if not available
        """
        # Determine schema filename based on type
        try:
            schema_filename = self._get_schema_filename(schema_type)
        except ValueError as e:
            logger.error(e)
            return None
        
        # Check if the schema file exists in cache
        schema_path = self.cache_dir / schema_type / schema_filename
        if schema_path.exists():
            return schema_path
        
        # If not found, try to download latest schemas
        logger.info(f"Schema file not found. Trying to download latest schemas...")
        if self.check_and_update_schemas(force=True):
            # Check again after download
            if schema_path.exists():
                return schema_path
        
        # If specific version requested and we don't have it, try to download directly
        if version != "latest":
            # Ensure version has 'v' prefix
            if not version.startswith('v'):
                version = f"v{version}"
            
            # Determine schema filename and release tag
            if schema_type == "package":
                filename = "hatch_pkg_metadata_schema.json"
                release_tag = f"schemas-package-{version}"
            else:
                filename = "hatch_all_pkg_metadata_schema.json"
                release_tag = f"schemas-registry-{version}"
            
            # Try to download specific version from release
            schema_url = f"{GITHUB_RELEASES_BASE}/{release_tag}/{filename}"
            try:
                logger.debug(f"Trying to download {schema_type} schema version {version} from {schema_url}")
                response = requests.get(schema_url, timeout=10)
                response.raise_for_status()
                
                # Save to cache
                schema_path.parent.mkdir(parents=True, exist_ok=True)
                with open(schema_path, "w") as f:
                    json.dump(response.json(), f, indent=2)
                return schema_path
            except requests.RequestException as e:
                logger.error(f"Error downloading {schema_type} schema version {version}: {e}")
            
        logger.error(f"Could not find or download schema: {schema_type} version {version}")
        return None

    def load_schema(self, schema_type: str, version: str = "latest") -> Optional[Dict[str, Any]]:
        """Load a schema from the cache. Will attempt to download if not found.
        
        Args:
            schema_type: Either "package" or "registry"
            version: Version of the schema, or "latest"
            
        Returns:
            The schema as a dictionary, or None if not available
        """
        # Get the schema path (this will handle downloading if needed)
        schema_path = self.get_schema_path(schema_type, version)
        if not schema_path:
            return None
        
        # Try to load the schema
        try:
            logger.debug(f"Loading {schema_type} schema from {schema_path}")
            with open(schema_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading {schema_type} schema: {e}")
            
            # If there's an error, the file might be corrupt - try to repair
            logger.info("Attempting to repair schema by forcing update...")
            if self.check_and_update_schemas(force=True):
                schema_path = self.get_schema_path(schema_type, version)
                if schema_path:
                    try:
                        with open(schema_path, "r") as f:
                            return json.load(f)
                    except (json.JSONDecodeError, IOError):
                        logger.error("Schema repair attempt failed.")
            
            return None

    def _get_schema_filename(self, schema_type: str) -> str:
        """Get the expected schema filename for a given schema type."""
        if schema_type == "package":
            return "hatch_pkg_metadata_schema.json"
        elif schema_type == "registry":
            return "hatch_all_pkg_metadata_schema.json"
        else:
            raise ValueError(f"Unknown schema type: {schema_type}")
            
    def _normalize_version(self, version: str) -> str:
        """Ensure version has 'v' prefix."""
        if version and not version.startswith('v'):
            return f"v{version}"
        return version
    
    def _resolve_version(self, schema_type: str, version: str = "latest") -> str:
        """Resolve version string to an actual version number.
        
        Args:
            schema_type: Either "package" or "registry"
            version: Version of the schema, or "latest"
            
        Returns:
            Resolved version string with 'v' prefix
        """
        if version != "latest":
            return self._normalize_version(version)
            
        # Get the latest version from cache info
        cached_info = self._get_cached_schema_info()
        version = cached_info.get(f"latest_{schema_type}_version")
        
        # Default to v1.2.0 if not found (current latest version)
        return self._normalize_version(version) if version else "v1.2.0"


# Create a default instance for easier imports
schema_retriever = SchemaRetriever()


def get_package_schema(version: str = "latest", force_update: bool = False) -> Optional[Dict[str, Any]]:
    """Helper function to get the package schema.
    
    Args:
        version: Version of the schema, or "latest"
        force_update: If True, force a check for updates
        
    Returns:
        The package schema as a dictionary, or None if not available
    """
    schema_retriever.check_and_update_schemas(force=force_update)
    
    # Use the schema retriever to load the schema
    return schema_retriever.load_schema("package", version)


def get_registry_schema(version: str = "latest", force_update: bool = False) -> Optional[Dict[str, Any]]:
    """Helper function to get the registry schema.
    
    Args:
        version: Version of the schema, or "latest"
        force_update: If True, force a check for updates
        
    Returns:
        The registry schema as a dictionary, or None if not available
    """
    schema_retriever.check_and_update_schemas(force=force_update)

    # Use the schema retriever to load the schema
    return schema_retriever.load_schema("registry", version)


# If run as script, perform a test
if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    
    # Test functionality
    print("Testing schema retriever...")
    
    # Force update of schemas
    updated = schema_retriever.check_and_update_schemas(force=True)
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