"""Unit tests for v1.1.0 dependency validation strategy.

This module tests the new dependency validation implementation that uses
the decoupled utility modules for graph operations, version constraints,
and registry interactions.
"""

import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch

from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.schemas.v1_1_0.dependency_validation_strategy import DependencyValidationV1_1_0


class TestDependencyValidationV1_1_0(unittest.TestCase):
    """Test cases for the DependencyValidationV1_1_0 strategy."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.strategy = DependencyValidationV1_1_0()
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Sample registry data
        self.registry_data = {
            "packages": {
                "package_a": {
                    "versions": {
                        "1.0.0": {"dependencies": []},
                        "2.0.0": {"dependencies": []}
                    }
                },
                "package_b": {
                    "versions": {
                        "1.5.0": {"dependencies": ["package_a"]}
                    }
                },
                "package_c": {
                    "version": "3.0.0",
                    "dependencies": []
                }
            }
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_context(self, allow_local=True, registry_data=None):
        """Create a test validation context.
        
        Args:
            allow_local (bool): Whether to allow local dependencies
            registry_data (dict): Registry data to use
            
        Returns:
            ValidationContext: Test validation context
        """
        return ValidationContext(
            package_dir=self.temp_dir,
            registry_data=registry_data or self.registry_data,
            allow_local_dependencies=allow_local
        )
    
    def test_validate_empty_dependencies(self):
        """Test validation with no dependencies."""
        metadata = {
            "hatch_dependencies": [],
            "python_dependencies": []
        }
        context = self._create_test_context()
        
        is_valid, errors = self.strategy.validate_dependencies(metadata, context)
        
        self.assertTrue(is_valid, "Empty dependencies should be valid")
        self.assertEqual(errors, [], "Empty dependencies should have no errors")
    
    def test_validate_missing_dependency_arrays(self):
        """Test validation when dependency arrays are missing."""
        metadata = {}  # No dependency arrays
        context = self._create_test_context()
        
        is_valid, errors = self.strategy.validate_dependencies(metadata, context)
        
        self.assertTrue(is_valid, "Missing dependency arrays should be valid (treated as empty)")
        self.assertEqual(errors, [], "Missing dependency arrays should have no errors")
    
    def test_validate_simple_registry_dependencies(self):
        """Test validation of simple registry dependencies."""
        metadata = {
            "hatch_dependencies": [
                {
                    "name": "package_a",
                    "version_constraint": ">=1.0.0",
                    "type": {"type": "registry"}
                },
                {
                    "name": "package_b",
                    "version_constraint": "~=1.5",
                    "type": {"type": "registry"}
                }
            ],
            "python_dependencies": [
                {
                    "name": "requests",
                    "version_constraint": ">=2.0.0"
                }
            ]
        }
        context = self._create_test_context()
        
        is_valid, errors = self.strategy.validate_dependencies(metadata, context)
        
        self.assertTrue(is_valid, f"Valid registry dependencies should pass validation. Errors: {errors}")
        self.assertEqual(errors, [], "Valid dependencies should have no errors")
    
    def test_validate_registry_dependency_not_found(self):
        """Test validation when registry dependency doesn't exist."""
        metadata = {
            "hatch_dependencies": [
                {
                    "name": "non_existent_package",
                    "version_constraint": ">=1.0.0",
                    "type": {"type": "registry"}
                }
            ]
        }
        context = self._create_test_context()
        
        is_valid, errors = self.strategy.validate_dependencies(metadata, context)
        
        self.assertFalse(is_valid, "Non-existent registry dependency should fail validation")
        self.assertGreater(len(errors), 0, "Should have errors for non-existent dependency")
        self.assertTrue(any("non_existent_package" in error for error in errors), 
                       "Error should mention the missing package")
    
    def test_validate_invalid_version_constraints(self):
        """Test validation with invalid version constraints."""
        metadata = {
            "hatch_dependencies": [
                {
                    "name": "package_a",
                    "version_constraint": "invalid_constraint",
                    "type": {"type": "registry"}
                }
            ],
            "python_dependencies": [
                {
                    "name": "requests",
                    "version_constraint": ">>invalid"
                }
            ]
        }
        context = self._create_test_context()
        
        is_valid, errors = self.strategy.validate_dependencies(metadata, context)
        
        self.assertFalse(is_valid, "Invalid version constraints should fail validation")
        self.assertGreaterEqual(len(errors), 2, "Should have errors for both invalid constraints")
    
    def test_validate_local_dependencies_allowed(self):
        """Test validation of local dependencies when allowed."""
        # Create a test local package
        local_pkg_dir = self.temp_dir / "local_package"
        local_pkg_dir.mkdir()
        
        local_metadata = {
            "name": "local_package",
            "version": "1.0.0",
            "hatch_dependencies": []
        }
        
        with open(local_pkg_dir / "hatch_metadata.json", 'w') as f:
            json.dump(local_metadata, f)
        
        metadata = {
            "hatch_dependencies": [
                {
                    "name": "local_package",
                    "version_constraint": ">=1.0.0",
                    "type": {
                        "type": "local",
                        "uri": f"file://{local_pkg_dir.relative_to(self.temp_dir)}"
                    }
                }
            ]
        }
        context = self._create_test_context(allow_local=True)
        
        is_valid, errors = self.strategy.validate_dependencies(metadata, context)
        
        self.assertTrue(is_valid, f"Valid local dependencies should pass validation. Errors: {errors}")
        self.assertEqual(errors, [], "Valid local dependencies should have no errors")
    
    def test_validate_local_dependencies_not_allowed(self):
        """Test validation of local dependencies when not allowed."""
        metadata = {
            "hatch_dependencies": [
                {
                    "name": "local_package",
                    "version_constraint": ">=1.0.0",
                    "type": {
                        "type": "local",
                        "uri": "file://./local_package"
                    }
                }
            ]
        }
        context = self._create_test_context(allow_local=False)
        
        is_valid, errors = self.strategy.validate_dependencies(metadata, context)
        
        self.assertFalse(is_valid, "Local dependencies should fail when not allowed")
        self.assertGreater(len(errors), 0, "Should have errors for disallowed local dependencies")
        self.assertTrue(any("not allowed" in error for error in errors), 
                       "Error should mention that local dependencies are not allowed")
    
    def test_validate_local_dependency_missing_uri(self):
        """Test validation of local dependency without URI."""
        metadata = {
            "hatch_dependencies": [
                {
                    "name": "local_package",
                    "version_constraint": ">=1.0.0",
                    "type": {"type": "local"}  # Missing URI
                }
            ]
        }
        context = self._create_test_context(allow_local=True)
        
        is_valid, errors = self.strategy.validate_dependencies(metadata, context)
        
        self.assertFalse(is_valid, "Local dependency without URI should fail validation")
        self.assertGreater(len(errors), 0, "Should have errors for missing URI")
    
    def test_validate_local_dependency_invalid_path(self):
        """Test validation of local dependency with non-existent path."""
        metadata = {
            "hatch_dependencies": [
                {
                    "name": "local_package",
                    "version_constraint": ">=1.0.0",
                    "type": {
                        "type": "local",
                        "uri": "file://./non_existent_package"
                    }
                }
            ]
        }
        context = self._create_test_context(allow_local=True)
        
        is_valid, errors = self.strategy.validate_dependencies(metadata, context)
        
        self.assertFalse(is_valid, "Local dependency with non-existent path should fail validation")
        self.assertGreater(len(errors), 0, "Should have errors for non-existent path")
    
    def test_validate_missing_dependency_names(self):
        """Test validation with dependencies missing names."""
        metadata = {
            "hatch_dependencies": [
                {
                    "version_constraint": ">=1.0.0",
                    "type": {"type": "registry"}
                }  # Missing name
            ],
            "python_dependencies": [
                {
                    "version_constraint": ">=2.0.0"
                }  # Missing name
            ]
        }
        context = self._create_test_context()
        
        is_valid, errors = self.strategy.validate_dependencies(metadata, context)
        
        self.assertFalse(is_valid, "Dependencies without names should fail validation")
        self.assertGreaterEqual(len(errors), 2, "Should have errors for both missing names")
    
    def test_detect_circular_dependencies(self):
        """Test detection of circular dependencies."""
        # Create local packages with circular dependencies
        pkg_a_dir = self.temp_dir / "package_a"
        pkg_b_dir = self.temp_dir / "package_b"
        pkg_a_dir.mkdir()
        pkg_b_dir.mkdir()
        
        # Package A depends on Package B
        pkg_a_metadata = {
            "name": "package_a",
            "version": "1.0.0",
            "hatch_dependencies": [
                {
                    "name": "package_b",
                    "type": {
                        "type": "local",
                        "uri": "file://package_b"  # Use simple path that will be resolved relative to package_dir
                    }
                }
            ]
        }
        
        # Package B depends on Package A (circular)
        pkg_b_metadata = {
            "name": "package_b",
            "version": "1.0.0",
            "hatch_dependencies": [
                {
                    "name": "package_a",
                    "type": {
                        "type": "local",
                        "uri": "file://package_a"  # Use simple path that will be resolved relative to package_dir
                    }
                }
            ]
        }
        
        with open(pkg_a_dir / "hatch_metadata.json", 'w') as f:
            json.dump(pkg_a_metadata, f)
        with open(pkg_b_dir / "hatch_metadata.json", 'w') as f:
            json.dump(pkg_b_metadata, f)
        
        # Create the parent directory containing both packages
        parent_dir = self.temp_dir
        
        # Copy package files to parent directory to ensure they're accessible
        with open(parent_dir / "package_a" / "hatch_metadata.json", 'w') as f:
            json.dump(pkg_a_metadata, f)
        with open(parent_dir / "package_b" / "hatch_metadata.json", 'w') as f:
            json.dump(pkg_b_metadata, f)
        
        # Test validation of package A (should detect circular dependency)
        metadata = pkg_a_metadata
        context = ValidationContext(
            package_dir=parent_dir,  # Use parent directory as package_dir so paths resolve correctly
            registry_data=self.registry_data,
            allow_local_dependencies=True
        )
        
        is_valid, errors = self.strategy.validate_dependencies(metadata, context)
        
        self.assertFalse(is_valid, "Circular dependencies should fail validation")
        self.assertGreater(len(errors), 0, "Should have errors for circular dependencies")
        self.assertTrue(any("circular" in error.lower() for error in errors), 
                      f"Error should mention circular dependency. Errors: {errors}")
    
    def test_validate_with_no_registry_data(self):
        """Test validation when no registry data is available."""
        metadata = {
            "hatch_dependencies": [
                {
                    "name": "package_a",
                    "version_constraint": ">=1.0.0",
                    "type": {"type": "registry"}
                }
            ]
        }
        context = self._create_test_context(registry_data=None)
        
        is_valid, errors = self.strategy.validate_dependencies(metadata, context)
        
        # Should not fail validation if no registry data available
        # (This is a policy decision - could be changed)
        self.assertTrue(is_valid, "Should not fail validation when no registry data available")
    
    def test_validate_unknown_dependency_type(self):
        """Test validation with unknown dependency type."""
        metadata = {
            "hatch_dependencies": [
                {
                    "name": "package_a",
                    "version_constraint": ">=1.0.0",
                    "type": {"type": "unknown_type"}
                }
            ]
        }
        context = self._create_test_context()
        
        is_valid, errors = self.strategy.validate_dependencies(metadata, context)
        
        self.assertFalse(is_valid, "Unknown dependency type should fail validation")
        self.assertGreater(len(errors), 0, "Should have errors for unknown dependency type")
        self.assertTrue(any("unknown" in error.lower() for error in errors), 
                       "Error should mention unknown dependency type")


class TestDependencyValidationIntegration(unittest.TestCase):
    """Integration tests comparing new implementation with existing behavior."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.new_strategy = DependencyValidationV1_1_0()
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Import the old strategy for comparison
        from hatch_validator.schemas.v1_1_0.schema_validators import DependencyValidation as OldDependencyValidation
        self.old_strategy = OldDependencyValidation()
        
        self.registry_data = {
            "packages": {
                "test_package": {
                    "versions": {
                        "1.0.0": {"dependencies": []},
                        "1.1.0": {"dependencies": []}
                    }
                }
            }
        }
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_comparison_simple_valid_dependencies(self):
        """Compare new and old implementations for simple valid dependencies."""
        metadata = {
            "hatch_dependencies": [
                {
                    "name": "test_package",
                    "version_constraint": ">=1.0.0",
                    "type": {"type": "registry"}
                }
            ],
            "python_dependencies": [
                {
                    "name": "requests",
                    "version_constraint": ">=2.0.0"
                }
            ]
        }
        
        context = ValidationContext(
            package_dir=self.temp_dir,
            registry_data=self.registry_data,
            allow_local_dependencies=True
        )
        
        # Test new implementation
        new_valid, new_errors = self.new_strategy.validate_dependencies(metadata, context)
        
        # Test old implementation
        old_valid, old_errors = self.old_strategy.validate_dependencies(metadata, context)
        
        # Both should give the same result for simple cases
        self.assertEqual(new_valid, old_valid, 
                        f"Both implementations should agree on validity. New: {new_errors}, Old: {old_errors}")
    
    def test_comparison_invalid_version_constraints(self):
        """Compare implementations for invalid version constraints."""
        metadata = {
            "hatch_dependencies": [
                {
                    "name": "test_package",
                    "version_constraint": "invalid>>constraint",
                    "type": {"type": "registry"}
                }
            ]
        }
        
        context = ValidationContext(
            package_dir=self.temp_dir,
            registry_data=self.registry_data,
            allow_local_dependencies=True
        )
        
        # Test new implementation
        new_valid, new_errors = self.new_strategy.validate_dependencies(metadata, context)
        
        # Test old implementation
        old_valid, old_errors = self.old_strategy.validate_dependencies(metadata, context)
        
        # Both should detect invalid constraints
        self.assertEqual(new_valid, old_valid, 
                        "Both implementations should agree on invalid constraints")
        self.assertFalse(new_valid, "Invalid constraints should fail validation in new implementation")
        self.assertFalse(old_valid, "Invalid constraints should fail validation in old implementation")


if __name__ == '__main__':
    unittest.main()
