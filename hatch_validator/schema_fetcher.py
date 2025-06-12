"""Schema fetching utility for retrieving schemas from GitHub.

This module provides functionality for:
1. Discovering latest schema versions via GitHub API
2. Downloading schemas directly from GitHub releases
"""

import json
import logging
from typing import Dict, Any, Optional

import requests

# Configure logging
logger = logging.getLogger("hatch.schema_fetcher")

# Configuration
GITHUB_API_BASE = "https://api.github.com/repos/crackingshells/Hatch-Schemas"
GITHUB_RELEASES_BASE = "https://github.com/crackingshells/Hatch-Schemas/releases/download"

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
        from datetime import datetime, timezone
        
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
