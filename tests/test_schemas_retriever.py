"""Integration tests for schemas_retriever with real network calls."""

import os
import unittest
from hatch_validator.schemas_retriever import get_package_schema, get_registry_schema

class TestSchemaRetrieverIntegration(unittest.TestCase):
    """Integration tests for schemas_retriever with real network calls."""

    def test_real_github_api_call(self):
        """Test real GitHub API call for schema info."""
        schema = get_package_schema(force_update=True)
        self.assertIsInstance(schema, dict, "Downloaded schema should be a dict")
        self.assertIn("title", schema, "Downloaded schema should contain a 'title' field")

    def test_real_registry_schema_download(self):
        """Test real registry schema download from GitHub."""
        schema = get_registry_schema(force_update=True)
        self.assertIsInstance(schema, dict, "Downloaded registry schema should be a dict")
        self.assertIn("title", schema, "Downloaded registry schema should contain a 'title' field")

    def test_real_specific_version_download(self):
        """Test real download of a specific schema version from GitHub."""
        schema = get_package_schema(version="1.2.0", force_update=True)
        self.assertIsInstance(schema, dict, "Downloaded specific version schema should be a dict")
        self.assertIn("title", schema, "Downloaded specific version schema should contain a 'title' field")

    def test_cache_behavior(self):
        """Test that schema is loaded from cache if not forcing update."""
        # First, force update to ensure schema is cached
        schema1 = get_package_schema(force_update=True)
        # Second, call without force_update (should use cache, not re-download)
        schema2 = get_package_schema(force_update=False)
        self.assertIsInstance(schema2, dict, "Schema loaded from cache should be a dict")
        self.assertEqual(schema1["title"], schema2["title"], "Schema loaded from cache should match the forced download")

if __name__ == "__main__":
    unittest.main()
