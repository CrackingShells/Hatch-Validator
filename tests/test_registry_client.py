"""Unit tests for registry client utilities.

This module tests the registry interaction functionality used for
package validation across different schema versions.
"""

import unittest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch

from hatch_validator.utils.registry_client import (
    RegistryPackageInfo,
    LocalFileRegistryClient,
    CachedRegistryClient,
    RegistryManager,
    RegistryError
)


class TestRegistryPackageInfo(unittest.TestCase):
    """Test cases for the RegistryPackageInfo class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.package_info = RegistryPackageInfo(
            name="test_package",
            versions=["1.0.0", "1.1.0", "2.0.0"],
            metadata={
                "description": "Test package",
                "versions": {
                    "1.0.0": {"dependencies": []},
                    "1.1.0": {"dependencies": ["other_pkg"]},
                    "2.0.0": {"dependencies": ["other_pkg>=1.0"]}
                }
            }
        )
    
    def test_has_version_exists(self):
        """Test checking for existing version."""
        self.assertTrue(self.package_info.has_version("1.0.0"), "Should find existing version 1.0.0")
        self.assertTrue(self.package_info.has_version("2.0.0"), "Should find existing version 2.0.0")
    
    def test_has_version_not_exists(self):
        """Test checking for non-existing version."""
        self.assertFalse(self.package_info.has_version("3.0.0"), "Should not find non-existing version 3.0.0")
        self.assertFalse(self.package_info.has_version("0.9.0"), "Should not find non-existing version 0.9.0")
    
    def test_get_latest_version(self):
        """Test getting the latest version."""
        latest = self.package_info.get_latest_version()
        # Note: This uses simple string sorting, so "2.0.0" should be latest
        self.assertIsNotNone(latest, "Should return a latest version")
        self.assertIn(latest, self.package_info.versions, "Latest version should be in available versions")
    
    def test_get_latest_version_empty(self):
        """Test getting latest version when no versions available."""
        empty_package = RegistryPackageInfo("empty", [], {})
        latest = empty_package.get_latest_version()
        self.assertIsNone(latest, "Should return None when no versions available")
    
    def test_get_metadata_for_version_exists(self):
        """Test getting metadata for existing version."""
        metadata = self.package_info.get_metadata_for_version("1.1.0")
        self.assertIsInstance(metadata, dict, "Should return dictionary metadata")
        expected_deps = ["other_pkg"]
        self.assertEqual(metadata.get("dependencies"), expected_deps, 
                        "Should return correct dependencies for version 1.1.0")
    
    def test_get_metadata_for_version_not_exists(self):
        """Test getting metadata for non-existing version."""
        metadata = self.package_info.get_metadata_for_version("3.0.0")
        self.assertIsInstance(metadata, dict, "Should return dictionary even for non-existing version")
        # Should return base metadata when specific version metadata not found
        self.assertEqual(metadata.get("description"), "Test package", 
                        "Should return base metadata for non-existing version")


class TestLocalFileRegistryClient(unittest.TestCase):
    """Test cases for the LocalFileRegistryClient class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary registry file
        self.temp_dir = tempfile.mkdtemp()
        self.registry_file = os.path.join(self.temp_dir, "test_registry.json")
        
        # Sample registry data
        self.sample_registry = {
            "packages": {
                "package1": {
                    "description": "First test package",
                    "versions": {
                        "1.0.0": {"dependencies": []},
                        "1.1.0": {"dependencies": ["package2"]}
                    }
                },
                "package2": {
                    "description": "Second test package",
                    "version": "2.0.0",
                    "dependencies": []
                }
            }
        }
        
        # Write sample data to file
        with open(self.registry_file, 'w') as f:
            json.dump(self.sample_registry, f)
        
        self.client = LocalFileRegistryClient(self.registry_file)
    
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.registry_file):
            os.remove(self.registry_file)
        os.rmdir(self.temp_dir)
    
    def test_load_registry_data_success(self):
        """Test successful loading of registry data."""
        result = self.client.load_registry_data()
        self.assertTrue(result, "Should successfully load registry data")
        self.assertTrue(self.client.is_loaded(), "Client should report as loaded")
        self.assertEqual(self.client.registry_data, self.sample_registry, 
                        "Loaded data should match file contents")
    
    def test_load_registry_data_file_not_found(self):
        """Test loading with non-existent file."""
        non_existent_file = os.path.join(self.temp_dir, "non_existent.json")
        client = LocalFileRegistryClient(non_existent_file)
        
        with self.assertRaises(RegistryError, msg="Should raise RegistryError for non-existent file"):
            client.load_registry_data()
    
    def test_load_registry_data_invalid_json(self):
        """Test loading with invalid JSON file."""
        invalid_json_file = os.path.join(self.temp_dir, "invalid.json")
        with open(invalid_json_file, 'w') as f:
            f.write("{ invalid json")
        
        client = LocalFileRegistryClient(invalid_json_file)
        
        with self.assertRaises(RegistryError, msg="Should raise RegistryError for invalid JSON"):
            client.load_registry_data()
        
        os.remove(invalid_json_file)
    
    def test_get_package_info_exists(self):
        """Test getting info for existing package."""
        package_info = self.client.get_package_info("package1")
        self.assertIsNotNone(package_info, "Should return RegistryPackageInfo for existing package")
        self.assertEqual(package_info.name, "package1", "Package name should match")
        self.assertIn("1.0.0", package_info.versions, "Should include version 1.0.0")
        self.assertIn("1.1.0", package_info.versions, "Should include version 1.1.0")
    
    def test_get_package_info_not_exists(self):
        """Test getting info for non-existing package."""
        package_info = self.client.get_package_info("non_existent")
        self.assertIsNone(package_info, "Should return None for non-existing package")
    
    def test_package_exists_true(self):
        """Test package existence check for existing package."""
        exists = self.client.package_exists("package1")
        self.assertTrue(exists, "Should return True for existing package")
    
    def test_package_exists_false(self):
        """Test package existence check for non-existing package."""
        exists = self.client.package_exists("non_existent")
        self.assertFalse(exists, "Should return False for non-existing package")
    
    def test_get_all_packages(self):
        """Test getting all package names."""
        packages = self.client.get_all_packages()
        expected_packages = ["package1", "package2"]
        self.assertEqual(sorted(packages), sorted(expected_packages), 
                        "Should return all package names from registry")
    
    def test_auto_load_on_first_access(self):
        """Test that registry data is automatically loaded on first access."""
        client = LocalFileRegistryClient(self.registry_file)
        self.assertFalse(client.is_loaded(), "Should not be loaded initially")
        
        # First access should trigger loading
        packages = client.get_all_packages()
        self.assertTrue(client.is_loaded(), "Should be loaded after first access")
        self.assertGreater(len(packages), 0, "Should return packages after auto-loading")


class TestCachedRegistryClient(unittest.TestCase):
    """Test cases for the CachedRegistryClient class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock base client
        self.mock_base_client = Mock()
        self.mock_base_client.is_loaded.return_value = True
        self.mock_base_client.load_registry_data.return_value = True
        
        # Mock package info
        self.mock_package_info = RegistryPackageInfo("test_pkg", ["1.0.0"], {})
        
        self.cached_client = CachedRegistryClient(self.mock_base_client)
    
    def test_get_package_info_caching(self):
        """Test that package info is cached."""
        self.mock_base_client.get_package_info.return_value = self.mock_package_info
        
        # First call should hit base client
        result1 = self.cached_client.get_package_info("test_pkg")
        self.assertEqual(result1, self.mock_package_info, "Should return package info from base client")
        self.mock_base_client.get_package_info.assert_called_once_with("test_pkg")
        
        # Second call should use cache
        self.mock_base_client.get_package_info.reset_mock()
        result2 = self.cached_client.get_package_info("test_pkg")
        self.assertEqual(result2, self.mock_package_info, "Should return same package info from cache")
        self.mock_base_client.get_package_info.assert_not_called()
    
    def test_get_all_packages_caching(self):
        """Test that all packages list is cached."""
        expected_packages = ["pkg1", "pkg2", "pkg3"]
        self.mock_base_client.get_all_packages.return_value = expected_packages
        
        # First call should hit base client
        result1 = self.cached_client.get_all_packages()
        self.assertEqual(result1, expected_packages, "Should return packages from base client")
        self.mock_base_client.get_all_packages.assert_called_once()
        
        # Second call should use cache
        self.mock_base_client.get_all_packages.reset_mock()
        result2 = self.cached_client.get_all_packages()
        self.assertEqual(result2, expected_packages, "Should return same packages from cache")
        self.mock_base_client.get_all_packages.assert_not_called()
    
    def test_cache_invalidation_on_load(self):
        """Test that cache is invalidated when loading new data."""
        self.mock_base_client.get_package_info.return_value = self.mock_package_info
        
        # Get package info to populate cache
        self.cached_client.get_package_info("test_pkg")
        self.mock_base_client.get_package_info.assert_called_once()
        
        # Load new data should invalidate cache
        self.cached_client.load_registry_data()
        
        # Next call should hit base client again
        self.mock_base_client.get_package_info.reset_mock()
        self.cached_client.get_package_info("test_pkg")
        self.mock_base_client.get_package_info.assert_called_once()
    
    def test_clear_cache_manually(self):
        """Test manual cache clearing."""
        self.mock_base_client.get_package_info.return_value = self.mock_package_info
        
        # Get package info to populate cache
        self.cached_client.get_package_info("test_pkg")
        self.mock_base_client.get_package_info.assert_called_once()
        
        # Clear cache manually
        self.cached_client.clear_cache()
        
        # Next call should hit base client again
        self.mock_base_client.get_package_info.reset_mock()
        self.cached_client.get_package_info("test_pkg")
        self.mock_base_client.get_package_info.assert_called_once()


class TestRegistryManager(unittest.TestCase):
    """Test cases for the RegistryManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a mock registry client
        self.mock_client = Mock()
        self.mock_client.is_loaded.return_value = True
        
        self.manager = RegistryManager(self.mock_client)
    
    def test_validate_package_exists_true(self):
        """Test package validation for existing package."""
        self.mock_client.package_exists.return_value = True
        
        valid, error = self.manager.validate_package_exists("existing_pkg")
        self.assertTrue(valid, "Should validate existing package as valid")
        self.assertIsNone(error, "Should not have error for existing package")
    
    def test_validate_package_exists_false(self):
        """Test package validation for non-existing package."""
        self.mock_client.package_exists.return_value = False
        
        valid, error = self.manager.validate_package_exists("non_existing_pkg")
        self.assertFalse(valid, "Should validate non-existing package as invalid")
        self.assertIsNotNone(error, "Should have error message for non-existing package")
        self.assertIn("non_existing_pkg", error, "Error should mention package name")
    
    def test_validate_package_version_exists(self):
        """Test version validation for existing version."""
        mock_package_info = RegistryPackageInfo("test_pkg", ["1.0.0", "2.0.0"], {})
        self.mock_client.get_package_info.return_value = mock_package_info
        
        valid, error = self.manager.validate_package_version("test_pkg", "1.0.0")
        self.assertTrue(valid, "Should validate existing version as valid")
        self.assertIsNone(error, "Should not have error for existing version")
    
    def test_validate_package_version_not_exists(self):
        """Test version validation for non-existing version."""
        mock_package_info = RegistryPackageInfo("test_pkg", ["1.0.0", "2.0.0"], {})
        self.mock_client.get_package_info.return_value = mock_package_info
        
        valid, error = self.manager.validate_package_version("test_pkg", "3.0.0")
        self.assertFalse(valid, "Should validate non-existing version as invalid")
        self.assertIsNotNone(error, "Should have error message for non-existing version")
        self.assertIn("3.0.0", error, "Error should mention version")
    
    def test_validate_package_version_package_not_exists(self):
        """Test version validation when package doesn't exist."""
        self.mock_client.get_package_info.return_value = None
        
        valid, error = self.manager.validate_package_version("non_existing_pkg", "1.0.0")
        self.assertFalse(valid, "Should validate as invalid when package doesn't exist")
        self.assertIsNotNone(error, "Should have error message when package doesn't exist")
        self.assertIn("non_existing_pkg", error, "Error should mention package name")
    
    def test_get_missing_packages(self):
        """Test getting list of missing packages."""
        # Mock some packages existing and some not
        def mock_package_exists(pkg_name):
            return pkg_name in ["existing1", "existing2"]
        
        self.mock_client.package_exists.side_effect = mock_package_exists
        
        packages_to_check = ["existing1", "missing1", "existing2", "missing2"]
        missing = self.manager.get_missing_packages(packages_to_check)
        
        expected_missing = ["missing1", "missing2"]
        self.assertEqual(sorted(missing), sorted(expected_missing), 
                        "Should return list of missing packages")
    
    def test_validate_dependency_list_all_valid(self):
        """Test dependency list validation when all are valid."""
        self.mock_client.package_exists.return_value = True
        
        dependencies = ["pkg1", "pkg2", "pkg3"]
        valid, errors = self.manager.validate_dependency_list(dependencies)
        
        self.assertTrue(valid, "Should validate as valid when all dependencies exist")
        self.assertEqual(errors, [], "Should have no errors when all dependencies exist")
    
    def test_validate_dependency_list_some_invalid(self):
        """Test dependency list validation when some are invalid."""
        def mock_package_exists(pkg_name):
            return pkg_name in ["pkg1", "pkg3"]
        
        self.mock_client.package_exists.side_effect = mock_package_exists
        
        dependencies = ["pkg1", "pkg2", "pkg3"]
        valid, errors = self.manager.validate_dependency_list(dependencies)
        
        self.assertFalse(valid, "Should validate as invalid when some dependencies don't exist")
        self.assertGreater(len(errors), 0, "Should have errors when some dependencies don't exist")
    
    def test_get_registry_statistics(self):
        """Test getting registry statistics."""
        # Mock registry data
        all_packages = ["pkg1", "pkg2", "pkg3"]
        self.mock_client.get_all_packages.return_value = all_packages
        
        # Mock package info with different version counts
        def mock_get_package_info(pkg_name):
            version_counts = {"pkg1": 2, "pkg2": 1, "pkg3": 3}
            versions = [f"{i}.0.0" for i in range(version_counts[pkg_name])]
            return RegistryPackageInfo(pkg_name, versions, {})
        
        self.mock_client.get_package_info.side_effect = mock_get_package_info
        
        stats = self.manager.get_registry_statistics()
        
        self.assertEqual(stats['total_packages'], 3, "Should count total packages correctly")
        self.assertEqual(stats['total_versions'], 6, "Should count total versions correctly")
        self.assertEqual(stats['average_versions_per_package'], 2.0, 
                        "Should calculate average versions per package correctly")


if __name__ == '__main__':
    unittest.main()
