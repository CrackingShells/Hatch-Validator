#!/usr/bin/env python3
import json
import unittest
import tempfile
import shutil
from pathlib import Path
import logging
import sys

# Add the parent directory to the path if needed
sys.path.insert(0, str(Path(__file__).parent.parent))

from hatch_validator.package_validator import HatchPackageValidator, PackageValidationError

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hatch.validator_tests")


class TestHatchPackageValidator(unittest.TestCase):
    """Tests for the Hatch package validator using real packages from Hatch-Dev."""

    def setUp(self):
        """Set up test environment before each test."""
        self.validator = HatchPackageValidator()
        
        # Path to Hatch-Dev packages
        self.hatch_dev_path = Path(__file__).parent.parent.parent / "Hatch-Dev"
        self.assertTrue(self.hatch_dev_path.exists(), 
                        f"Hatch-Dev directory not found at {self.hatch_dev_path}")
                        
        # Create list of available packages for dependency testing
        self.available_packages = self._build_available_packages()
        
    def _build_available_packages(self):
        """Build a list of available packages from Hatch-Dev for dependency testing."""
        packages = {}
        
        # Known packages in Hatch-Dev
        pkg_names = [
            "arithmetic_pkg", 
            "base_pkg_1", 
            "base_pkg_2", 
            "python_dep_pkg",
            "circular_dep_pkg_1"
        ]
        
        for pkg_name in pkg_names:
            pkg_path = self.hatch_dev_path / pkg_name
            if pkg_path.exists():
                metadata_path = pkg_path / "hatch_metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            packages[pkg_name] = metadata
                    except Exception as e:
                        logger.warning(f"Failed to load metadata for {pkg_name}: {e}")
        
        return packages
    
    def test_valid_package_arithmetic(self):
        """Test validating a simple valid package (arithmetic_pkg)."""
        pkg_path = self.hatch_dev_path / "arithmetic_pkg"
        is_valid, results = self.validator.validate_package(pkg_path)
        
        self.assertTrue(is_valid)
        self.assertTrue(results["valid"])
        self.assertTrue(results["metadata_schema"]["valid"])
        self.assertTrue(results["entry_point"]["valid"])
        self.assertTrue(results["tools"]["valid"])
        self.assertTrue(results["dependencies"]["valid"])
        
    def test_valid_package_with_dependencies(self):
        """Test validating a package with valid dependencies (simple_dep_pkg)."""
        # # First make sure the dependency exists in available_packages
        # base_pkg_path = self.hatch_dev_path / "base_pkg_1"
        # base_metadata_path = base_pkg_path / "hatch_metadata.json"
        # with open(base_metadata_path, 'r') as f:
        #     base_metadata = json.load(f)
            
        # # Add to available packages
        # base_pkg = {
        #     "name": base_metadata.get("name"),
        #     "version": base_metadata.get("version")
        # }
        # available_packages = self.available_packages + [base_pkg]
        
        # Now validate the package that depends on it
        pkg_path = self.hatch_dev_path / "simple_dep_pkg"
        is_valid, results = self.validator.validate_package(pkg_path, self.available_packages)
        
        self.assertTrue(is_valid)
        self.assertTrue(results["valid"])
        self.assertTrue(results["dependencies"]["valid"])
    
    def test_missing_dependency(self):
        """Test validating a package with missing dependencies (missing_dep_pkg)."""
        pkg_path = self.hatch_dev_path / "missing_dep_pkg"
        is_valid, results = self.validator.validate_package(pkg_path, self.available_packages)
        
        self.assertFalse(is_valid)
        self.assertFalse(results["valid"])
        self.assertFalse(results["dependencies"]["valid"])
        self.assertTrue(len(results["dependencies"]["errors"]) > 0)
        
        # Check if the error message mentions the missing dependency
        any_error_mentions_missing = any("not found in available packages" in error 
                                        for error in results["dependencies"]["errors"])
        self.assertTrue(any_error_mentions_missing)
    
    def test_complex_dependency_chain(self):
        """Test validating a package with complex dependency chain (complex_dep_pkg)."""
        # Build available packages list with all required dependencies
        # required_deps = ["base_pkg_1", "base_pkg_2", "python_dep_pkg"]
        # available_packages = self.available_packages.copy()
        
        # for dep_name in required_deps:
        #     dep_path = self.hatch_dev_path / dep_name
        #     metadata_path = dep_path / "hatch_metadata.json"
        #     if metadata_path.exists():
        #         with open(metadata_path, 'r') as f:
        #             metadata = json.load(f)
        #             # Add or update in available packages
        #             available_packages.append({
        #                 "name": metadata.get("name"),
        #                 "version": metadata.get("version")
        #             })
        
        # Now validate the complex dependency package
        pkg_path = self.hatch_dev_path / "complex_dep_pkg"
        is_valid, results = self.validator.validate_package(pkg_path, self.available_packages)
        
        self.assertTrue(is_valid)
        self.assertTrue(results["valid"])
        self.assertTrue(results["dependencies"]["valid"])
    
    def test_version_dependency_constraint(self):
        """Test validating a package with version-specific dependency (version_dep_pkg)."""
        # # Add the base package with a compatible version
        # base_pkg = {
        #     "name": "base_pkg_1",
        #     "version": "1.0.0"  # This should satisfy >=0.1.0
        # }
        # available_packages = self.available_packages + [base_pkg]
        
        # Validate the package with version-specific dependency
        pkg_path = self.hatch_dev_path / "version_dep_pkg"
        is_valid, results = self.validator.validate_package(pkg_path, self.available_packages)
        
        self.assertTrue(is_valid)
        self.assertTrue(results["valid"])
        self.assertTrue(results["dependencies"]["valid"])
    
    def test_version_dependency_constraint_incompatible(self):
        """Test validating a package with incompatible version dependency."""
        # Add the base package with an incompatible version
        # base_pkg = {
        #     "name": "base_pkg_1", 
        #     "version": "0.0.9"  # This should NOT satisfy >=0.1.0
        # }
        
        # Make a copy of the available packages to avoid modifying the original
        available_packages = self.available_packages.copy()
        # Modify the version of the base package for this test
        self.available_packages["base_pkg_1"]["version"] = "0.0.9"

        
        # Validate the package with version-specific dependency
        pkg_path = self.hatch_dev_path / "version_dep_pkg"
        is_valid, results = self.validator.validate_package(pkg_path, available_packages)
        
        self.assertFalse(is_valid)
        self.assertFalse(results["valid"])
        self.assertFalse(results["dependencies"]["valid"])
        
        # Check if error message mentions version mismatch
        any_error_mentions_version = any("does not satisfy constraint" in error 
                                        for error in results["dependencies"]["errors"])
        self.assertTrue(any_error_mentions_version)
        
    def test_circular_dependency_packages(self):
        """Test validating packages involved in a circular dependency."""
        # This is testing at the package level - circular dependencies are typically
        # detected at the registry level with multiple packages
        
        # First package (circular_dep_pkg_1)
        pkg1_path = self.hatch_dev_path / "circular_dep_pkg_1"
        is_valid1, results1 = self.validator.validate_package(pkg1_path, self.available_packages)
        
        # circular_dep_pkg_1 should not be valid since it depends on circular_dep_pkg_2
        self.assertFalse(is_valid1)
        self.assertFalse(results1["valid"])
        self.assertFalse(results1["dependencies"]["valid"])
        
        # Then, let's make the second package available
        pkg2_path = self.hatch_dev_path / "circular_dep_pkg_2"
        with open(pkg2_path / "hatch_metadata.json", 'r') as f:
            metadata = json.load(f)
            # make a copy of the available packages to avoid modifying the original
            available_packages = self.available_packages.copy()
            # Expand the copy to include the second package
            available_packages["circular_dep_pkg_2"] = metadata

        # Test the first package again with the second one available
        is_valid1bis, results1bis = self.validator.validate_package(pkg1_path, available_packages)

        self.assertTrue(is_valid1bis)
        self.assertTrue(results1bis["valid"])
        self.assertTrue(results1bis["dependencies"]["valid"])

        # Now, modify the data of the second package to create a circular dependency
        # Let's add a dependency field to the metadata in the available packages
        available_packages["circular_dep_pkg_2"]["hatch_dependencies"] = [{"name": "circular_dep_pkg_1", "version": "1.0.0", "type": "remote"}]

        # Finally, re-run validation for the first package
        # This should now fail due to circular dependency
        is_valid1ter, results1ter = self.validator.validate_package(pkg1_path, available_packages)

        self.assertFalse(is_valid1ter)
        self.assertFalse(results1ter["valid"])
        self.assertFalse(results1ter["dependencies"]["valid"])
    
    def test_entry_point_not_exists(self):
        """Test validating a package with a missing entry point file."""
        
        #TODO: This test is self implemented, we should rely on a dummy package instead
        # in "Hatch-Dev" to test this case. Something like "missing_entry_point_pkg"
        
        # Create a temporary package with an invalid entry point
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Copy a valid package
            pkg_path = temp_dir / "test_pkg"
            shutil.copytree(self.hatch_dev_path / "arithmetic_pkg", pkg_path)
            
            # Modify the metadata to point to a non-existent entry point
            metadata_path = pkg_path / "hatch_metadata.json"
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                
            metadata["entry_point"] = "non_existent_file.py"
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            # Validate the package
            is_valid, results = self.validator.validate_package(pkg_path)
            
            self.assertFalse(is_valid)
            self.assertFalse(results["valid"])
            self.assertFalse(results["entry_point"]["valid"])
            self.assertTrue(len(results["entry_point"]["errors"]) > 0)
            
        finally:
            # Clean up
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    unittest.main()