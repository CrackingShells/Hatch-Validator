#!/usr/bin/env python
"""
Schema Retriever Module

This module handles:
1. Fetching the latest schema information from the official source
2. Downloading and caching schema files locally
3. Providing access to schema files for validation
"""

import os
import json
import shutil
import logging
import requests
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Configure logging
logger = logging.getLogger("hatch.schema_retriever")
logger.setLevel(logging.INFO)

# Configuration
SCHEMA_INFO_URL = "https://crackingshells.github.io/Hatch-Schemas/latest.json"
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
            logger.debug(f"Requesting schema info from {SCHEMA_INFO_URL}")
            response = requests.get(SCHEMA_INFO_URL, timeout=10)
            response.raise_for_status()
            schema_info = response.json()
            logger.debug("Schema info retrieved successfully")
            
            # Add a timestamp for cache freshness tracking
            schema_info["updated_at"] = datetime.now().astimezone().isoformat()
            return schema_info
        except requests.RequestException as e:
            logger.error(f"Error fetching schema info: {e}")
            return {}

    def _download_and_extract_schema(self, schema_type: str, version: str, download_url: str) -> bool:
        """Download and extract schema files to the cache directory for a specific schema type.
        
        Args:
            schema_type: Either "package" or "registry"
            version: The version of the schema (e.g., "v1")
            download_url: URL to download the schema ZIP archive
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a temporary file to download to
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
                temp_path = temp_file.name
            
            # Download the schema zip
            logger.info(f"Downloading {schema_type} schema version {version} from {download_url}")
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Save to temporary file
            with open(temp_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Create the schema version directory
            schema_version_dir = self.cache_dir / schema_type / version
            schema_version_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine the expected schema filename based on schema type
            expected_filename = self._get_schema_filename(schema_type)
            found_schema = False
            
            # Extract the zip file to the schema version directory
            with zipfile.ZipFile(temp_path, 'r') as zip_ref:
                logger.debug(f"Extracting {schema_type} schema to {schema_version_dir}")
                file_list = zip_ref.namelist()
                logger.debug(f"Files in ZIP: {file_list}")
                
                # Search strategy:
                # 1. First look in version directories (e.g., v1/schema.json)
                # 2. Then look at the top level for the expected filename
                # 3. Then look for any JSON file that contains the schema type name
                # 4. Finally just extract all JSON files
                
                # Search patterns in order of preference
                search_patterns = [
                    # Pattern 1: vX/expected_filename.json
                    lambda f: f.startswith('v') and f.endswith(f'/{expected_filename}'),
                    # Pattern 2: expected_filename.json at root
                    lambda f: f == expected_filename,
                    # Pattern 3: Any JSON with schema type in the name
                    lambda f: f.endswith('.json') and schema_type in f.lower(),
                    # Pattern 4: Any JSON file
                    lambda f: f.endswith('.json')
                ]
                
                for pattern in search_patterns:
                    matches = [f for f in file_list if pattern(f)]
                    if matches:
                        match = matches[0]  # Take the first match
                        logger.info(f"Found schema file: {match}")
                        schema_data = zip_ref.read(match)
                        with open(schema_version_dir / expected_filename, 'wb') as f:
                            f.write(schema_data)
                        found_schema = True
                        break
                
                # If we're using the "any JSON" pattern (last resort), log a warning
                if found_schema and pattern == search_patterns[-1]:
                    logger.warning(f"Used generic JSON file as {schema_type} schema: {match}")
            
            # Create or update a "latest" marker file
            latest_file = self.cache_dir / schema_type / "latest"
            with open(latest_file, 'w') as f:
                f.write(version)
            
            # Clean up the temporary file
            os.unlink(temp_path)
            
            # If we couldn't find the schema in the ZIP, check if it exists in the local repository
            if not found_schema:
                # Try to find the schema in the local Hatch-Schemas repository
                local_paths = [
                    Path(__file__).parent.parent / "Hatch-Schemas" / schema_type / version / expected_filename,
                    Path(__file__).parent.parent / "Hatch-Schemas" / schema_type / "v1" / expected_filename
                ]
                
                for local_schema in local_paths:
                    if local_schema.exists():
                        logger.info(f"Found schema at {local_schema}. Copying to {schema_version_dir / expected_filename}")
                        shutil.copy(local_schema, schema_version_dir / expected_filename)
                        found_schema = True
                        break
            
            if found_schema:
                logger.debug(f"{schema_type.capitalize()} schema extraction completed successfully")
                return True
            else:
                logger.error(f"Could not find {expected_filename} in the downloaded archive or in local repository")
                return False
                
        except Exception as e:
            logger.error(f"Error downloading {schema_type} schema: {e}", exc_info=True)
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
            # Check cache freshness
            last_updated = cached_info.get("updated_at")
            if last_updated:
                try:
                    last_updated_dt = datetime.fromisoformat(last_updated.replace("Z", "+00:00"))
                    cache_age = datetime.now().astimezone() - last_updated_dt
                    
                    # Cache is stale
                    if cache_age >= timedelta(seconds=DEFAULT_CACHE_DURATION):
                        need_to_fetch = True
                        logger.info("Schema cache is stale. Checking for updates.")
                    else:
                        logger.info(f"Using cached schema info (last updated: {last_updated})")
                        
                        # Verify schema files exist as a secondary check
                        for schema_type in ["package", "registry"]:
                            if schema_type not in cached_info:
                                continue
                                
                            # Get version from cache info
                            version = (cached_info.get(schema_type, {}).get("version") or 
                                      cached_info.get(f"latest_{schema_type}_version", "v1"))
                            
                            version = self._normalize_version(version)
                            
                            # Determine schema filename
                            schema_filename = self._get_schema_filename(schema_type)
                            schema_path = self.cache_dir / schema_type / version / schema_filename
                            
                            if not schema_path.exists():
                                logger.warning(f"Schema file {schema_path} referenced in cache doesn't exist.")
                                need_to_fetch = True
                                break
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
        
        # Set a timestamp in the latest info for caching purposes
        latest_info["updated_at"] = datetime.now().astimezone().isoformat()
        
        updated = False
        
        # Process each schema type
        for schema_type in ["package", "registry"]:
            if schema_type not in latest_info:
                continue
                
            # Get latest version info
            latest_version_key = f"latest_{schema_type}_version"
            latest_version = latest_info.get(latest_version_key)
            
            if not latest_version:
                continue
            
            # Ensure version has 'v' prefix
            latest_version = self._normalize_version(latest_version)
            latest_info[latest_version_key] = latest_version
            
            # Determine if we need to update this schema
            needs_update = True
            
            # Skip update if:
            # 1. Not forcing update
            # 2. We have cached info
            # 3. The cached version matches the latest version
            # 4. The schema file actually exists
            if not force and cached_info and schema_type in cached_info:
                cached_version = (cached_info.get(schema_type, {}).get("version") or 
                                 cached_info.get(f"latest_{schema_type}_version"))
                
                cached_version = self._normalize_version(cached_version)
                
                if cached_version == latest_version:
                    # Check if file exists
                    schema_filename = self._get_schema_filename(schema_type)
                    schema_path = self.cache_dir / schema_type / latest_version / schema_filename
                    
                    if schema_path.exists():
                        logger.info(f"{schema_type.capitalize()} schema is up to date (version {latest_version}).")
                        needs_update = False
            
            # Update schema if needed
            if needs_update:
                download_url = latest_info.get(schema_type, {}).get("download_url")
                if download_url:
                    logger.info(f"New {schema_type} schema version available: {latest_version}")
                    if self._download_and_extract_schema(schema_type, latest_version, download_url):
                        updated = True
                        logger.info(f"{schema_type.capitalize()} schema updated successfully.")
                        
                        # Update schema info in the latest_info
                        if schema_type not in latest_info:
                            latest_info[schema_type] = {}
                        latest_info[schema_type]["version"] = latest_version
                    else:
                        logger.error(f"{schema_type.capitalize()} schema update failed.")
                else:
                    logger.warning(f"No download URL found for {schema_type} schema")
        
        # Always update cache info after checking, even if nothing changed
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
        
        # First try: Get the schema at the specified or resolved latest version
        path = self._try_get_schema_at_version(schema_type, version, schema_filename)
        if path:
            return path
        
        # Second try: Download schemas and try again with potentially updated versions
        logger.info(f"Schema file not found. Trying to download latest schemas...")
        if self.check_and_update_schemas(force=True):
            # If "latest" was requested, always use whatever is latest now after download
            if version == "latest":
                latest_version = self._resolve_version(schema_type, "latest")
                logger.info(f"Using freshly downloaded latest schema version: {latest_version}")
                path = self._try_get_schema_at_version(schema_type, "latest", schema_filename)
                if path:
                    return path
            else:
                # For specific version requests, try the requested version first
                path = self._try_get_schema_at_version(schema_type, version, schema_filename)
                if path:
                    return path
                
                # If still not found, try using the latest version as fallback
                latest_version = self._resolve_version(schema_type, "latest")
                if latest_version != version:
                    logger.info(f"Version {version} not found, trying latest ({latest_version})")
                    path = self._try_get_schema_at_version(schema_type, "latest", schema_filename)
                    if path:
                        return path
        
        logger.error(f"Could not find or download schema: {schema_type} version {version}")
        
        return None
        
    def _try_get_schema_at_version(self, schema_type: str, version: str, schema_filename: str) -> Optional[Path]:
        """Helper method to try getting a schema at a specific version.
        
        Args:
            schema_type: Either "package" or "registry"
            version: Version of the schema, or "latest"
            schema_filename: Filename of the schema
            
        Returns:
            Path to the schema file if found, otherwise None
        """
        # If "latest" is requested, resolve it
        if version == "latest":
            version = self._resolve_version(schema_type, "latest")
        else:
            version = self._normalize_version(version)
        
        # Check if the schema file exists
        schema_path = self.cache_dir / schema_type / version / schema_filename
        if schema_path.exists():
            return schema_path
            
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
            
        # Try to get the version from the marker file first
        latest_file = self.cache_dir / schema_type / "latest"
        if latest_file.exists():
            try:
                with open(latest_file, 'r') as f:
                    return self._normalize_version(f.read().strip())
            except IOError:
                pass
        
        # If no marker file or error reading it, fall back to cache info
        cached_info = self._get_cached_schema_info()
        version = cached_info.get(f"latest_{schema_type}_version")
        
        # Default to v1 if not found
        return self._normalize_version(version) if version else "v1"


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