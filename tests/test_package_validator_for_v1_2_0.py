#!/usr/bin/env python3
import json
import unittest
import tempfile
import shutil
from pathlib import Path
import logging
import sys
from datetime import datetime

# Add the parent directory to the path if needed
sys.path.insert(0, str(Path(__file__).parent.parent))

from hatch_validator.package_validator import HatchPackageValidator, PackageValidationError
from hatch_validator.registry.registry_service import RegistryService

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("hatch.validator_tests_v1_2_0")
logger.setLevel(logging.DEBUG)


class TestHatchPackageValidator_v1_2_0(unittest.TestCase):
    """Tests for the Hatch package validator using real packages from Hatch-Dev including
    packages following schema versions:
      - 1.1.0: <Put here all package folder names that follow this schema>
      - 1.2.0: <Put here all package folder names that follow this schema>
    """
    
    def setUp(self):
        """Set up test environment before each test."""
        # Path to Hatch-Dev packages
        self.hatch_dev_path = Path(__file__).parent.parent.parent / "Hatching-Dev"
        self.assertTrue(self.hatch_dev_path.exists(), 
                        f"Hatch-Dev directory not found at {self.hatch_dev_path}")
                        
        # Build registry data structure from Hatch-Dev packages
        self.registry_data = self._build_test_registry()

        # Create registry service with the test data
        self.registry_service = RegistryService(self.registry_data)

        # Create validator with registry data
        self.validator = HatchPackageValidator(registry_data=self.registry_data)
        
    def _build_test_registry(self):
        """
        Build a test registry data structure from Hatch-Dev packages for dependency testing.
        This simulates the structure that would be expected from a real registry file.
        """
        # Create registry structure according to the schema
        registry = {
            "registry_schema_version": "1.1.0",
            "last_updated": datetime.now().isoformat(),
            "repositories": [
                {
                    "name": "Hatch-Dev",
                    "url": "file://" + str(self.hatch_dev_path),
                    "packages": [],
                    "last_indexed": datetime.now().isoformat()
                }
            ]
        }
        
        # Known packages in Hatch-Dev
        pkg_dirs = [
            "base_pkg_1_4_0", 
            "base_pkg_2_1_1_0", 
            "python_dep_pkg_1_1_0",
            "circular_dep_pkg_1_1_1_0",
            "circular_dep_pkg_2_2_0_0",
            "complex_dep_pkg_1_1_0",
            "simple_dep_pkg_1_1_0",
            "missing_dep_pkg_1_1_0",
            "version_dep_pkg_1_1_0",
            "system_dep_pkg",
            "docker_dep_pkg"
        ]
        
        # Add each package to the registry
        for pkg_name in pkg_dirs:
            pkg_path = self.hatch_dev_path / pkg_name
            if pkg_path.exists():
                metadata_path = pkg_path / "hatch_metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            deps = metadata.get("dependencies", {})

                            # Create a package entry with version information
                            pkg_entry = {
                                "name": metadata.get("name", pkg_name),
                                "description": metadata.get("description", ""),
                                "category": "development",
                                "tags": metadata.get("tags", []),
                                "latest_version": metadata.get("version", "1.0.0"),
                                "versions": [
                                    {
                                        "version": metadata.get("version", "1.0.0"),
                                        "release_uri": f"file://{pkg_path}",
                                        "author": {
                                            "GitHubID": metadata.get("author", {}).get("name", "test_user"),
                                            "email": metadata.get("author", {}).get("email", "test@example.com")
                                        },
                                        "added_date": datetime.now().isoformat(),
                                        # Add dependencies as differential changes
                                        "hatch_dependencies_added": deps.get("hatch", []),
                                        "python_dependencies_added": deps.get("python", []),
                                    }
                                ]
                            }
                            
                            # Add to registry
                            registry["repositories"][0]["packages"].append(pkg_entry)
                    except Exception as e:
                        logger.error(f"Failed to load metadata for {pkg_name}: {e}")
                        raise e

        return registry
    
    def test_valid_package_arithmetic(self):
        """Test validating a simple valid package (arithmetic_pkg_1_2_0)."""
        pkg_path = self.hatch_dev_path / "arithmetic_pkg_1_2_0"
        is_valid, results = self.validator.validate_package(pkg_path)
        
        self.assertTrue(is_valid, f"Package validation failed for arithmetic_pkg_1_2_0. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid")
        self.assertTrue(results["metadata_schema"]["valid"], f"Schema validation failed: {results.get('metadata_schema', {}).get('errors')}")
        self.assertTrue(results["entry_point"]["valid"], f"Entry point validation failed: {results.get('entry_point', {}).get('errors')}")
        self.assertTrue(results["tools"]["valid"], f"Tools validation failed: {results.get('tools', {}).get('errors')}")
        self.assertTrue(results["dependencies"]["valid"], f"Dependencies validation failed: {results.get('dependencies', {}).get('errors')}")
    
    def test_valid_package_with_dependencies(self):
        """Test validating a package with valid dependencies (simple_dep_pkg_1_1_0)."""
        pkg_path = self.hatch_dev_path / "simple_dep_pkg_1_1_0"
        with open(pkg_path / "hatch_metadata.json", 'r') as f:
            metadata = json.load(f)
            is_valid, results = self.validator.validate_package(pkg_path, pending_update=(metadata.get("name"), metadata))
        
            self.assertTrue(is_valid, f"Package validation failed for simple_dep_pkg_1_1_0. Errors: {results}")
            self.assertTrue(results["valid"], f"Overall validation result should be valid for simple_dep_pkg_1_1_0")
            self.assertTrue(results["dependencies"]["valid"], f"Dependencies validation failed for simple_dep_pkg_1_1_0: {results.get('dependencies', {}).get('errors')}")
    
    def test_missing_dependency(self):
        """Test validating a package with missing dependencies (missing_dep_pkg_1_1_0)."""
        pkg_path = self.hatch_dev_path / "missing_dep_pkg_1_1_0"
        is_valid, results = self.validator.validate_package(pkg_path)
        
        self.assertFalse(is_valid, f"Package validation should fail for missing_dep_pkg_1_1_0.")
        self.assertFalse(results["valid"], f"Overall validation result should be invalid for missing_dep_pkg_1_1_0")
        self.assertFalse(results["dependencies"]["valid"], f"Dependencies validation should fail for missing_dep_pkg_1_1_0")
        self.assertTrue(len(results["dependencies"]["errors"]) > 0, f"Missing dependency should produce error messages")
        
        # Check if the error message mentions the missing dependency
        any_error_mentions_missing = any("not found in registry" in error 
                                        for error in results["dependencies"]["errors"])
        error_messages = "\n - ".join(results.get("dependencies", {}).get("errors", ["No errors"]))
        self.assertTrue(any_error_mentions_missing, f"Error should mention dependency not found. Actual errors: \n - {error_messages}")
    
    def test_complex_dependency_chain(self):
        """Test validating a package with complex dependency chain (complex_dep_pkg_1_1_0)."""
        pkg_path = self.hatch_dev_path / "complex_dep_pkg_1_1_0"
        is_valid, results = self.validator.validate_package(pkg_path)
        
        self.assertTrue(is_valid, f"Package validation failed for complex_dep_pkg_1_1_0. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for complex_dep_pkg_1_1_0")
        self.assertTrue(results["dependencies"]["valid"], f"Dependencies validation failed for complex_dep_pkg_1_1_0: {results.get('dependencies', {}).get('errors')}")
    
    def test_version_dependency_constraint(self):
        """Test validating a package with version-specific dependency (version_dep_pkg_1_1_0)."""
        pkg_path = self.hatch_dev_path / "version_dep_pkg_1_1_0"
        is_valid, results = self.validator.validate_package(pkg_path)
        
        self.assertTrue(is_valid, f"Package validation failed for version_dep_pkg_1_1_0. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for version_dep_pkg_1_1_0")
        self.assertTrue(results["dependencies"]["valid"], f"Dependencies validation failed for version_dep_pkg_1_1_0: {results.get('dependencies', {}).get('errors')}")
    
    def test_version_dependency_constraint_incompatible(self):
        """Test validating a package with incompatible version dependency (version_dep_pkg_1_1_0)."""
        # Create a copy of the registry with an incompatible version
        modified_registry = self.registry_data.copy()
        
        # Find base_pkg_1 in the registry
        for repo in modified_registry["repositories"]:
            for pkg in repo["packages"]:
                if pkg["name"] == "base_pkg_1":
                    # Change the version to be incompatible
                    pkg["latest_version"] = "0.0.9"
                    pkg["versions"][0]["version"] = "0.0.9"        

        # Create a new validator with the modified registry
        validator = HatchPackageValidator(registry_data=modified_registry)

        # Validate the package with version-specific dependency
        pkg_path = self.hatch_dev_path / "version_dep_pkg_1_1_0"
        is_valid, results = validator.validate_package(pkg_path)
        
        # No need to reset anything with RegistryService - each validator gets its own instance
        
        self.assertFalse(is_valid, f"Package validation should fail with incompatible version.")
        self.assertFalse(results["valid"], f"Overall validation result should be invalid for incompatible version")
        self.assertFalse(results["dependencies"]["valid"], f"Dependencies validation should fail for incompatible version")
        
        # Check if error message mentions version mismatch
        any_error_mentions_version = any("satisfies constraint" in error 
                                        for error in results["dependencies"]["errors"])
        error_messages = "\n - ".join(results.get("dependencies", {}).get("errors", ["No errors"]))
        self.assertTrue(any_error_mentions_version, f"Error should mention version constraint. Actual errors: \n - {error_messages}")
    
    def test_circular_dependency_packages(self):
        """Test validating packages involved in a circular dependency (circular_dep_pkg_2_2_0_0_next_v)."""
        pkg_path = self.hatch_dev_path / "circular_dep_pkg_2_2_0_0_next_v"

        with open(pkg_path / "hatch_metadata.json", 'r') as f:
            metadata = json.load(f)
            is_valid, results = self.validator.validate_package(pkg_path, (metadata.get("name"), metadata))

            self.assertFalse(is_valid, f"Package validation should fail for circular dependency.")
            self.assertFalse(results["valid"], f"Overall validation result should be invalid for circular dependency")
            self.assertFalse(results["dependencies"]["valid"], f"Dependencies validation should fail for circular dependency")
            
            any_error_mentions_circular = any("circular" in error.lower() for error in results["dependencies"]["errors"])
            error_messages = "\n - ".join(results.get("dependencies", {}).get("errors", ["No errors"]))
            self.assertTrue(any_error_mentions_circular, f"Error should mention circular dependency. Actual errors: \n - {error_messages}")
        
    def test_entry_point_not_exists(self):
        """Test validating a package with a missing entry point file (arithmetic_pkg_1_2_0)."""
        # Create a temporary package with an invalid entry point
        temp_dir = Path(tempfile.mkdtemp())
        try:
            # Copy a valid package
            pkg_path = temp_dir / "test_pkg"
            shutil.copytree(self.hatch_dev_path / "arithmetic_pkg_1_2_0", pkg_path)
            
            # Modify the metadata to point to a non-existent entry point
            metadata_path = pkg_path / "hatch_metadata.json"
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                
            metadata["entry_point"] = "non_existent_file.py"
            
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f)
            
            # Validate the package
            is_valid, results = self.validator.validate_package(pkg_path)

            self.assertFalse(is_valid, f"Package validation should fail for non_existent_entry_point.")
            self.assertFalse(results["valid"], f"Overall validation result should be invalid for non_existent_entry_point")
            self.assertFalse(results["entry_point"]["valid"], f"Entry point validation should fail for non_existent_entry_point")
            self.assertTrue(len(results["entry_point"]["errors"]) > 0, f"Entry point errors should be present for non_existent_entry_point")

        finally:
            # Clean up
            shutil.rmtree(temp_dir)

    def test_valid_system_dependency(self):
        """Test validating a package with a valid system dependency (system_dep_pkg)."""
        pkg_path = self.hatch_dev_path / "system_dep_pkg"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertTrue(is_valid, f"Package validation failed for system_dep_pkg. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for system_dep_pkg")
        self.assertTrue(results["dependencies"]["valid"], f"System dependency validation failed: {results.get('dependencies', {}).get('errors')}")

    def test_valid_docker_dependency(self):
        """Test validating a package with a valid docker dependency (docker_dep_pkg)."""
        pkg_path = self.hatch_dev_path / "docker_dep_pkg"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertTrue(is_valid, f"Package validation failed for docker_dep_pkg. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for docker_dep_pkg")
        self.assertTrue(results["dependencies"]["valid"], f"Docker dependency validation failed: {results.get('dependencies', {}).get('errors')}")

    def test_valid_python_dependency(self):
        """Test validating a package with a valid Python dependency (python_dep_pkg)."""
        pkg_path = self.hatch_dev_path / "python_dep_pkg"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertTrue(is_valid, f"Package validation failed for python_dep_pkg. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for python_dep_pkg")
        self.assertTrue(results["dependencies"]["valid"], f"Python dependency validation failed: {results.get('dependencies', {}).get('errors')}")

    def test_valid_python_dependency_v1_2_0(self):
        """Test validating a v1.2.0 package with a valid Python dependency (python_dep_pkg_1_1_0)."""
        pkg_path = self.hatch_dev_path / "python_dep_pkg_1_1_0"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertTrue(is_valid, f"Package validation failed for python_dep_pkg_1_1_0. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for python_dep_pkg_1_1_0")
        self.assertTrue(results["dependencies"]["valid"], f"Python dependency validation failed: {results.get('dependencies', {}).get('errors')}")

    def test_valid_arithmetic_pkg_v1_2_0(self):
        """Test validating arithmetic_pkg_1_2_0 (v1.2.0 schema)."""
        pkg_path = self.hatch_dev_path / "arithmetic_pkg_1_2_0"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertTrue(is_valid, f"Package validation failed for arithmetic_pkg_1_2_0. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for arithmetic_pkg_1_2_0")
        self.assertTrue(results["dependencies"]["valid"], f"Dependency validation failed: {results.get('dependencies', {}).get('errors')}")

    def test_valid_base_pkg_1_v1_4_0(self):
        """Test validating base_pkg_1_4_0 (v1.2.0 schema)."""
        pkg_path = self.hatch_dev_path / "base_pkg_1_4_0"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertTrue(is_valid, f"Package validation failed for base_pkg_1_4_0. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for base_pkg_1_4_0")
        self.assertTrue(results["dependencies"]["valid"], f"Dependency validation failed: {results.get('dependencies', {}).get('errors')}")

    def test_valid_base_pkg_2_v1_1_0(self):
        """Test validating base_pkg_2_1_0 (v1.2.0 schema)."""
        pkg_path = self.hatch_dev_path / "base_pkg_2_1_0"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertTrue(is_valid, f"Package validation failed for base_pkg_2_1_0. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for base_pkg_2_1_0")
        self.assertTrue(results["dependencies"]["valid"], f"Dependency validation failed: {results.get('dependencies', {}).get('errors')}")

    def test_valid_circular_dep_pkg_1_v1_1_0(self):
        """Test validating circular_dep_pkg_1_1_0 (v1.2.0 schema)."""
        pkg_path = self.hatch_dev_path / "circular_dep_pkg_1_1_0"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertTrue(is_valid, f"Package validation failed for circular_dep_pkg_1_1_0. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for circular_dep_pkg_1_1_0")
        self.assertTrue(results["dependencies"]["valid"], f"Dependency validation failed: {results.get('dependencies', {}).get('errors')}")

    def test_valid_circular_dep_pkg_2_v2_0_0(self):
        """Test validating circular_dep_pkg_2_2_0_0 (v1.2.0 schema)."""
        pkg_path = self.hatch_dev_path / "circular_dep_pkg_2_2_0_0"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertTrue(is_valid, f"Package validation failed for circular_dep_pkg_2_2_0_0. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for circular_dep_pkg_2_2_0_0")
        self.assertTrue(results["dependencies"]["valid"], f"Dependency validation failed: {results.get('dependencies', {}).get('errors')}")

    def test_valid_complex_dep_pkg_v1_1_0(self):
        """Test validating complex_dep_pkg_1_1_0 (v1.2.0 schema)."""
        pkg_path = self.hatch_dev_path / "complex_dep_pkg_1_1_0"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertTrue(is_valid, f"Package validation failed for complex_dep_pkg_1_1_0. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for complex_dep_pkg_1_1_0")
        self.assertTrue(results["dependencies"]["valid"], f"Dependency validation failed: {results.get('dependencies', {}).get('errors')}")

    def test_valid_missing_dep_pkg_v1_1_0(self):
        """Test validating missing_dep_pkg_1_1_0 (v1.2.0 schema, should fail)."""
        pkg_path = self.hatch_dev_path / "missing_dep_pkg_1_1_0"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertFalse(is_valid, f"Package validation should fail for missing_dep_pkg_1_1_0.")
        self.assertFalse(results["valid"], f"Overall validation result should be invalid for missing_dep_pkg_1_1_0")
        self.assertFalse(results["dependencies"]["valid"], f"Dependency validation should fail for missing_dep_pkg_1_1_0")

    def test_valid_simple_dep_pkg_v1_1_0(self):
        """Test validating simple_dep_pkg_1_1_0 (v1.2.0 schema)."""
        pkg_path = self.hatch_dev_path / "simple_dep_pkg_1_1_0"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertTrue(is_valid, f"Package validation failed for simple_dep_pkg_1_1_0. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for simple_dep_pkg_1_1_0")
        self.assertTrue(results["dependencies"]["valid"], f"Dependency validation failed: {results.get('dependencies', {}).get('errors')}")

    def test_valid_version_dep_pkg_v1_1_0(self):
        """Test validating version_dep_pkg_1_1_0 (v1.2.0 schema)."""
        pkg_path = self.hatch_dev_path / "version_dep_pkg_1_1_0"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertTrue(is_valid, f"Package validation failed for version_dep_pkg_1_1_0. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for version_dep_pkg_1_1_0")
        self.assertTrue(results["dependencies"]["valid"], f"Dependency validation failed: {results.get('dependencies', {}).get('errors')}")

    def test_valid_local_path_dep_pkg(self):
        """Test validating a v1.2.0 package with a valid local path dependency (local_path_dep_pkg)."""
        pkg_path = self.hatch_dev_path / "local_path_dep_pkg"
        is_valid, results = self.validator.validate_package(pkg_path)

        self.assertTrue(is_valid, f"Package validation failed for local_path_dep_pkg. Errors: {results}")
        self.assertTrue(results["valid"], f"Overall validation result should be valid for local_path_dep_pkg")
        self.assertTrue(results["dependencies"]["valid"], f"Dependency validation failed: {results.get('dependencies', {}).get('errors')}")

    def test_nonexistent_repo_dep_pkg(self):
        """Test validating a v1.2.0 package with a dependency on a non-existent repository prefix (nonexistent_repo_dep_pkg)."""
        pkg_path = self.hatch_dev_path / "nonexistent_repo_dep_pkg"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertFalse(is_valid, f"Package validation should fail for nonexistent_repo_dep_pkg.")
        self.assertFalse(results["valid"], f"Overall validation result should be invalid for nonexistent_repo_dep_pkg")
        self.assertFalse(results["dependencies"]["valid"], f"Dependency validation should fail for nonexistent_repo_dep_pkg")
        self.assertTrue(any("Repository" in err for err in results["dependencies"].get("errors", [])), "Error should mention missing repository.")

    def test_file_path_dep_pkg(self):
        """Test validating a v1.2.0 package with a local dependency that is a file, not a directory (file_path_dep_pkg)."""
        pkg_path = self.hatch_dev_path / "file_path_dep_pkg"
        is_valid, results = self.validator.validate_package(pkg_path)
        self.assertFalse(is_valid, f"Package validation should fail for file_path_dep_pkg.")
        self.assertFalse(results["valid"], f"Overall validation result should be invalid for file_path_dep_pkg")
        self.assertFalse(results["dependencies"]["valid"], f"Dependency validation should fail for file_path_dep_pkg")
        self.assertTrue(any("not a directory" in err.lower() for err in results["dependencies"].get("errors", [])), "Error should mention not a directory.")
        
if __name__ == "__main__":
    unittest.main()