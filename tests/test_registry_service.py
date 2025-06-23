#!/usr/bin/env python3
"""Tests for the RegistryService and registry accessors (v1.1.0).

This module tests the RegistryService API for access operations on a mock registry
following the v1.1.0 schema.
"""
import unittest
from hatch_validator.registry.registry_service import RegistryService, RegistryError

# Minimal mock registry data following v1.1.0 schema
MOCK_REGISTRY_V110 = {
    "registry_schema_version": "1.1.0",
    "last_updated": "2025-06-23T12:00:00Z",
    "repositories": [
        {
            "name": "Hatch-Dev",
            "url": "https://example.com/hatch-dev",
            "last_indexed": "2025-06-23T12:00:00Z",
            "packages": [
                {
                    "name": "base_pkg_1",
                    "description": "Base package 1.",
                    "tags": ["core", "base"],
                    "versions": [
                        {
                            "author": "Alice",
                            "version": "1.0.0",
                            "release_uri": "https://example.com/hatch-dev/base_pkg_1/1.0.0",
                            "added_date": "2025-06-23T12:00:00Z",
                            "hatch_dependencies_added": [],
                            "hatch_dependencies_removed": []
                        },
                        {
                            "author": "Alice",
                            "version": "1.1.0",
                            "release_uri": "https://example.com/hatch-dev/base_pkg_1/1.1.0",
                            "added_date": "2025-06-23T12:00:00Z",
                            "hatch_dependencies_added": [],
                            "hatch_dependencies_removed": []
                        }
                    ],
                    "latest_version": "1.1.0"
                },
                {
                    "name": "util_pkg",
                    "description": "Utility package.",
                    "tags": ["util"],
                    "versions": [
                        {
                            "author": "Bob",
                            "version": "0.1.0",
                            "release_uri": "https://example.com/hatch-dev/util_pkg/0.1.0",
                            "added_date": "2025-06-23T12:00:00Z",
                            "hatch_dependencies_added": [
                                {"name": "base_pkg_1", "type": "remote", "version_constraint": ">=1.0.0"}
                            ],
                            "hatch_dependencies_removed": []
                        }
                    ],
                    "latest_version": "0.1.0"
                }
            ]
        }
    ],
    "stats": {
        "total_packages": 2,
        "total_versions": 3
    }
}

class TestRegistryServiceV110(unittest.TestCase):
    """Tests for RegistryService access operations on v1.1.0 mock registry."""

    def setUp(self):
        self.service = RegistryService(MOCK_REGISTRY_V110)

    def test_is_loaded(self):
        self.assertTrue(self.service.is_loaded())

    def test_list_repositories(self):
        repos = self.service.list_repositories()
        self.assertIn("Hatch-Dev", repos)

    def test_repository_exists(self):
        self.assertTrue(self.service.repository_exists("Hatch-Dev"))
        self.assertFalse(self.service.repository_exists("NonexistentRepo"))

    def test_list_packages(self):
        pkgs = self.service.list_packages("Hatch-Dev")
        self.assertIn("base_pkg_1", pkgs)
        self.assertIn("util_pkg", pkgs)

    def test_get_all_package_names(self):
        all_pkgs = self.service.get_all_package_names()
        self.assertIn("base_pkg_1", all_pkgs)
        self.assertIn("util_pkg", all_pkgs)
        # Test with repo_name
        repo_pkgs = self.service.get_all_package_names("Hatch-Dev")
        self.assertIn("base_pkg_1", repo_pkgs)
        self.assertIn("util_pkg", repo_pkgs)

    def test_package_exists(self):
        self.assertTrue(self.service.package_exists("base_pkg_1"))
        self.assertTrue(self.service.package_exists("Hatch-Dev:base_pkg_1"))
        self.assertFalse(self.service.package_exists("nonexistent_pkg"))
        # With repo_name argument
        self.assertTrue(self.service.package_exists("base_pkg_1", repo_name="Hatch-Dev"))
        self.assertFalse(self.service.package_exists("nonexistent_pkg", repo_name="Hatch-Dev"))

    def test_get_package_versions(self):
        versions = self.service.get_package_versions("base_pkg_1")
        self.assertEqual(sorted(versions), ["1.0.0", "1.1.0"])
        # With repo_name
        versions2 = self.service.get_package_versions("base_pkg_1", repo_name="Hatch-Dev")
        self.assertEqual(versions, versions2)
        # With repo name in package name
        versions3 = self.service.get_package_versions("Hatch-Dev:base_pkg_1")
        self.assertEqual(versions, versions3)

    def test_get_package_version_info(self):
        info = self.service.get_package_version_info("base_pkg_1", "1.1.0")
        self.assertEqual(info["version"], "1.1.0")
        self.assertEqual(info["release_uri"], "https://example.com/hatch-dev/base_pkg_1/1.1.0")
        # With repo_name
        info2 = self.service.get_package_version_info("base_pkg_1", "1.1.0", repo_name="Hatch-Dev")
        self.assertEqual(info, info2)
        # With repo name in package name
        info3 = self.service.get_package_version_info("Hatch-Dev:base_pkg_1", "1.1.0")
        self.assertEqual(info, info3)

    def test_get_package_dependencies(self):
        deps = self.service.get_package_dependencies("util_pkg", version="0.1.0")
        self.assertIn("dependencies", deps)
        self.assertEqual(deps["dependencies"][0]["name"], "base_pkg_1")
        # With repo_name
        deps2 = self.service.get_package_dependencies("util_pkg", version="0.1.0", repo_name="Hatch-Dev")
        self.assertEqual(deps, deps2)
        # With repo name in package name
        deps3 = self.service.get_package_dependencies("Hatch-Dev:util_pkg", version="0.1.0")
        self.assertEqual(deps, deps3)

    def test_get_package_uri(self):
        uri = self.service.get_package_uri("base_pkg_1", "1.0.0")
        self.assertEqual(uri, "https://example.com/hatch-dev/base_pkg_1/1.0.0")
        # With repo_name
        uri2 = self.service.get_package_uri("base_pkg_1", "1.0.0", repo_name="Hatch-Dev")
        self.assertEqual(uri, uri2)
        # With repo name in package name
        uri3 = self.service.get_package_uri("Hatch-Dev:base_pkg_1", "1.0.0")
        self.assertEqual(uri, uri3)

    def test_find_compatible_version(self):
        v = self.service.find_compatible_version("base_pkg_1", ">=1.0.0")
        self.assertIn(v, ["1.0.0", "1.1.0"])
        # With repo_name
        v2 = self.service.find_compatible_version("base_pkg_1", ">=1.0.0", repo_name="Hatch-Dev")
        self.assertIn(v2, ["1.0.0", "1.1.0"])
        # With repo name in package name
        v3 = self.service.find_compatible_version("Hatch-Dev:base_pkg_1", ">=1.0.0")
        self.assertIn(v3, ["1.0.0", "1.1.0"])

    def test_has_repository_name(self):
        self.assertTrue(self.service.has_repository_name("Hatch-Dev:base_pkg_1"))
        self.assertFalse(self.service.has_repository_name("base_pkg_1"))

    def test_get_package_by_repo(self):
        pkg = self.service.get_package_by_repo("Hatch-Dev", "base_pkg_1")
        self.assertIsNotNone(pkg)
        self.assertEqual(pkg["name"], "base_pkg_1")
        self.assertIsNone(self.service.get_package_by_repo("Hatch-Dev", "nonexistent"))

    def test_registry_statistics(self):
        stats = self.service.get_registry_statistics()
        self.assertEqual(stats["total_packages"], 2)
        self.assertEqual(stats["total_versions"], 3)
        self.assertGreater(stats["average_versions_per_package"], 0)

    def test_get_registry_data(self):
        data = self.service.get_registry_data()
        self.assertIsInstance(data, dict)
        self.assertEqual(data["registry_schema_version"], "1.1.0")

    def test_get_schema_version(self):
        self.assertEqual(self.service.get_schema_version(), "1.1.0")

if __name__ == "__main__":
    unittest.main()
