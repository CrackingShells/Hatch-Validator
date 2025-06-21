#!/usr/bin/env python3
"""Tests for the PackageService and package accessors (v1.1.0 and v1.2.0).

This module tests the version-aware package service and concrete accessors
using dummy package metadata for both v1.1.0 and v1.2.0 schemas.
"""
import unittest
from hatch_validator.package.package_service import PackageService

# Dummy package metadata for v1.1.0
DUMMY_METADATA_V110 = {
    "package_schema_version": "1.1.0",
    "name": "dummy_pkg_v110",
    "version": "0.1.0",
    "description": "A dummy package for v1.1.0 schema.",
    "tags": ["test", "dummy"],
    "author": {"name": "Alice", "email": "alice@example.com"},
    "contributors": [{"name": "Bob"}],
    "license": {"name": "MIT"},
    "repository": "https://example.com/repo",
    "documentation": "https://example.com/docs",
    "hatch_dependencies": [
        {"name": "base_pkg_1", "type": "remote", "version_constraint": ">=1.0.0"}
    ],
    "python_dependencies": [
        {"name": "requests", "version_constraint": ">=2.0.0", "package_manager": "pip"}
    ],
    "compatibility": {"hatchling": ">=0.1.0", "python": ">=3.7"},
    "entry_point": "dummy_pkg_v110.main:main",
    "tools": [{"name": "tool1", "description": "A tool"}],
    "citations": {"origin": "", "mcp": ""}
}

# Dummy package metadata for v1.2.0
DUMMY_METADATA_V120 = {
    "package_schema_version": "1.2.0",
    "name": "dummy_pkg_v120",
    "version": "0.2.0",
    "description": "A dummy package for v1.2.0 schema.",
    "tags": ["test", "dummy"],
    "author": {"name": "Carol", "email": "carol@example.com"},
    "contributors": [{"name": "Dave"}],
    "license": {"name": "Apache-2.0"},
    "repository": "https://example.com/repo2",
    "documentation": "https://example.com/docs2",
    "dependencies": {
        "hatch": [
            {"name": "base_pkg_2", "version_constraint": ">=2.0.0"}
        ],
        "python": [
            {"name": "numpy", "version_constraint": ">=1.18.0", "package_manager": "pip"}
        ],
        "system": [
            {"name": "libssl", "version_constraint": ">=1.1.1", "package_manager": "apt"}
        ],
        "docker": [
            {"name": "ubuntu", "version_constraint": "==20.04", "registry": "dockerhub"}
        ]
    },
    "compatibility": {"hatchling": ">=0.2.0", "python": ">=3.8"},
    "entry_point": "dummy_pkg_v120.main:main",
    "tools": [{"name": "tool2", "description": "Another tool"}],
    "citations": {"origin": "", "mcp": ""}
}

class TestPackageService(unittest.TestCase):
    """Tests for the PackageService and concrete package accessors."""

    def test_v110_fields(self):
        """Test all top-level fields for v1.1.0 dummy package."""
        service = PackageService(DUMMY_METADATA_V110)
        self.assertTrue(service.is_loaded())
        self.assertEqual(service.get_field("name"), "dummy_pkg_v110")
        self.assertEqual(service.get_field("version"), "0.1.0")
        self.assertEqual(service.get_field("author")["name"], "Alice")
        self.assertEqual(service.get_field("entry_point"), "dummy_pkg_v110.main:main")
        self.assertEqual(service.get_field("tools")[0]["name"], "tool1")
        deps = service.get_dependencies()
        self.assertIn("hatch", deps)
        self.assertIn("python", deps)
        self.assertEqual(deps["hatch"][0]["name"], "base_pkg_1")
        self.assertEqual(deps["python"][0]["name"], "requests")

    def test_v120_fields(self):
        """Test all top-level fields for v1.2.0 dummy package."""
        service = PackageService(DUMMY_METADATA_V120)
        self.assertTrue(service.is_loaded())
        self.assertEqual(service.get_field("name"), "dummy_pkg_v120")
        self.assertEqual(service.get_field("version"), "0.2.0")
        self.assertEqual(service.get_field("author")["name"], "Carol")
        self.assertEqual(service.get_field("entry_point"), "dummy_pkg_v120.main:main")
        self.assertEqual(service.get_field("tools")[0]["name"], "tool2")
        deps = service.get_dependencies()
        self.assertIn("hatch", deps)
        self.assertIn("python", deps)
        self.assertIn("system", deps)
        self.assertIn("docker", deps)
        self.assertEqual(deps["hatch"][0]["name"], "base_pkg_2")
        self.assertEqual(deps["python"][0]["name"], "numpy")
        self.assertEqual(deps["system"][0]["name"], "libssl")
        self.assertEqual(deps["docker"][0]["name"], "ubuntu")

if __name__ == "__main__":
    unittest.main()
