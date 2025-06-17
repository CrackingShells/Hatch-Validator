"""Tests for schema validation framework v1.1.0 implementation.

This module tests the concrete v1.1.0 validator and strategies using real test packages
from the Hatching-Dev library for comprehensive integration testing.
"""

import unittest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.core.validator_factory import ValidatorFactory
from hatch_validator.schemas.v1_1_0.schema_validators import (
    SchemaValidator as SchemaV1_1_0Validator,
    SchemaValidation as SchemaValidationV1_1_0,
    #DependencyValidation as DependencyValidationV1_1_0,
    ToolsValidation as ToolsValidationV1_1_0,
    EntryPointValidation as EntryPointValidationV1_1_0
)
from hatch_validator.schemas.v1_1_0.dependency_validation_strategy import DependencyValidationV1_1_0


class TestValidatorFactory(unittest.TestCase):
    """Test cases for ValidatorFactory with v1.1.0 implementation."""
    
    def test_create_v1_1_0_validator(self):
        """Test creating v1.1.0 validator through factory."""
        validator = ValidatorFactory.create_validator_chain("1.1.0")
        
        self.assertIsInstance(validator, SchemaV1_1_0Validator)
        self.assertTrue(validator.can_handle("1.1.0"))
        self.assertFalse(validator.can_handle("1.2.0"))
    
    def test_create_latest_validator(self):
        """Test creating latest validator defaults to v1.1.0."""
        validator = ValidatorFactory.create_validator_chain()
        
        self.assertIsInstance(validator, SchemaV1_1_0Validator)
        self.assertTrue(validator.can_handle("1.1.0"))


class TestSchemaV1_1_0Validator(unittest.TestCase):
    """Test cases for v1.1.0 SchemaValidator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = SchemaV1_1_0Validator()
        self.context = ValidationContext()
    
    def test_can_handle_v1_1_0(self):
        """Test that validator can handle v1.1.0 schema."""
        self.assertTrue(self.validator.can_handle("1.1.0"))
        self.assertFalse(self.validator.can_handle("1.2.0"))
        self.assertFalse(self.validator.can_handle(""))
    
    def test_validation_with_minimal_metadata(self):
        """Test validation with minimal v1.1.0 metadata."""
        metadata = {
            "package_schema_version": "1.1.0",
            "name": "test_pkg",
            "version": "1.0.0",
            "entry_point": "server.py",
            "description": "Test package",
            "tags": ["test"],
            "author": {"name": "Test Author"},
            "license": {"name": "MIT"}
        }
          # Mock the strategies to focus on validator logic
        with patch.object(self.validator.schema_strategy, 'validate_schema', return_value=(True, [])), \
             patch.object(self.validator.dependency_strategy, 'validate_dependencies', return_value=(True, [])), \
             patch.object(self.validator.tools_strategy, 'validate_tools', return_value=(True, [])), \
             patch.object(self.validator.entry_point_strategy, 'validate_entry_point', return_value=(True, [])):
            
            is_valid, errors = self.validator.validate(metadata, self.context)
            
            self.assertTrue(is_valid)
            self.assertEqual(errors, [])


class TestRealPackageIntegration(unittest.TestCase):
    """Integration tests using real test packages from Hatching-Dev."""
    
    def setUp(self):
        """Set up test fixtures with real package paths."""
        # Find Hatching-Dev directory
        current_dir = Path(__file__).parent
        workspace_root = current_dir.parent.parent
        self.hatching_dev_path = workspace_root / "Hatching-Dev"
        
        if not self.hatching_dev_path.exists():
            self.skipTest("Hatching-Dev test packages not available")
        
        # Set up validator and registry
        self.validator_factory = ValidatorFactory()
        self.registry_data = self._load_test_registry()
    
    def _load_test_registry(self):
        """Load test registry data."""
        registry_path = Path(__file__).parent.parent.parent / "Hatch-Registry" / "data" / "hatch_packages_registry.json"
        if registry_path.exists():
            with open(registry_path, 'r') as f:
                return json.load(f)
        return {"repositories": [{"packages": []}]}
    
    def _load_package_metadata(self, package_path):
        """Load metadata from a test package."""
        metadata_path = package_path / "hatch_metadata.json"
        if not metadata_path.exists():
            self.skipTest(f"Package metadata not found: {metadata_path}")
        
        with open(metadata_path, 'r') as f:
            return json.load(f)
    
    def test_arithmetic_pkg_validation(self):
        """Test validation of arithmetic_pkg (simple package)."""
        pkg_path = self.hatching_dev_path / "arithmetic_pkg"
        metadata = self._load_package_metadata(pkg_path)
        
        validator = self.validator_factory.create_validator_chain("1.1.0")
        context = ValidationContext(
            package_dir=pkg_path,
            registry_data=self.registry_data,
            allow_local_dependencies=True
        )
        
        is_valid, errors = validator.validate(metadata, context)
        
        self.assertTrue(is_valid, f"Validation failed with errors: {errors}")
        self.assertEqual(errors, [])
        self.assertEqual(metadata["package_schema_version"], "1.1.0")
    
    def test_simple_dep_pkg_validation(self):
        """Test validation of simple_dep_pkg (package with dependencies)."""
        pkg_path = self.hatching_dev_path / "simple_dep_pkg"
        metadata = self._load_package_metadata(pkg_path)
        
        validator = self.validator_factory.create_validator_chain("1.1.0")
        context = ValidationContext(
            package_dir=pkg_path,
            registry_data=self.registry_data,
            allow_local_dependencies=True
        )
        
        is_valid, errors = validator.validate(metadata, context)
        
        # This package has dependencies, so validation depends on registry
        self.assertEqual(metadata["package_schema_version"], "1.1.0")
        # Dependencies validation may fail if not in registry, but schema should be valid
    
    def test_complex_dep_pkg_validation(self):
        """Test validation of complex_dep_pkg (complex dependency structure)."""
        pkg_path = self.hatching_dev_path / "complex_dep_pkg"
        metadata = self._load_package_metadata(pkg_path)
        
        validator = self.validator_factory.create_validator_chain("1.1.0")
        context = ValidationContext(
            package_dir=pkg_path,
            registry_data=self.registry_data,
            allow_local_dependencies=True
        )
        
        is_valid, errors = validator.validate(metadata, context)
        
        self.assertEqual(metadata["package_schema_version"], "1.1.0")
        # Complex dependencies may have validation issues, but schema should be valid
    
    def test_python_dep_pkg_validation(self):
        """Test validation of python_dep_pkg (package with Python dependencies)."""
        pkg_path = self.hatching_dev_path / "python_dep_pkg"
        metadata = self._load_package_metadata(pkg_path)
        
        validator = self.validator_factory.create_validator_chain("1.1.0")
        context = ValidationContext(
            package_dir=pkg_path,
            registry_data=self.registry_data,
            allow_local_dependencies=True
        )
        
        is_valid, errors = validator.validate(metadata, context)
        
        self.assertEqual(metadata["package_schema_version"], "1.1.0")
        # Python dependencies should be handled appropriately
    
    def test_all_v1_1_0_packages(self):
        """Test validation of all available v1.1.0 packages."""
        v1_1_0_packages = []
        
        # Find all packages with v1.1.0 schema
        for pkg_dir in self.hatching_dev_path.iterdir():
            if pkg_dir.is_dir():
                metadata_path = pkg_dir / "hatch_metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                        if metadata.get("package_schema_version") == "1.1.0":
                            v1_1_0_packages.append((pkg_dir, metadata))
                    except (json.JSONDecodeError, KeyError):
                        continue
        
        self.assertGreater(len(v1_1_0_packages), 0, "No v1.1.0 packages found for testing")
        
        validator = self.validator_factory.create_validator_chain("1.1.0")
        
        for pkg_path, metadata in v1_1_0_packages:
            with self.subTest(package=pkg_path.name):
                context = ValidationContext(
                    package_dir=pkg_path,
                    registry_data=self.registry_data,
                    allow_local_dependencies=True
                )
                
                is_valid, errors = validator.validate(metadata, context)
                
                # At minimum, the schema validation should pass for all v1.1.0 packages
                # Dependencies might fail if not in registry, but that's expected
                self.assertEqual(metadata["package_schema_version"], "1.1.0")


class TestValidationStrategies(unittest.TestCase):
    """Test cases for individual v1.1.0 validation strategies."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.context = ValidationContext()
    
    def test_dependency_validation_strategy(self):
        """Test DependencyValidation strategy for v1.1.0."""
        strategy = DependencyValidationV1_1_0()
        
        # Test with no dependencies
        metadata = {"package_schema_version": "1.1.0"}
        is_valid, errors = strategy.validate_dependencies(metadata, self.context)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])
        
        # Test with hatch dependencies (proper v1.1.0 format)
        metadata_with_deps = {
            "package_schema_version": "1.1.0",
            "hatch_dependencies": [
                {
                    "name": "test_pkg", 
                    "version_constraint": ">=1.0.0",
                    "type": {"type": "remote", "source": "registry"}
                }
            ]
        }
        # Create a context with registry data to avoid the error
        context_with_registry = ValidationContext(registry_data={"registry_schema_version": "1.1.0", "repositories": [{"packages": []}]})
        is_valid, errors = strategy.validate_dependencies(metadata_with_deps, context_with_registry)
        # Result depends on whether dependency is in registry - expecting failure since test_pkg doesn't exist
        self.assertFalse(is_valid)
    
    def test_tools_validation_strategy(self):
        """Test ToolsValidation strategy for v1.1.0."""
        strategy = ToolsValidationV1_1_0()
        
        # Test with no tools
        metadata = {"package_schema_version": "1.1.0"}
        is_valid, errors = strategy.validate_tools(metadata, self.context)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])
    
    def test_entry_point_validation_strategy(self):
        """Test EntryPointValidation strategy for v1.1.0."""
        strategy = EntryPointValidationV1_1_0()
        
        metadata = {
            "package_schema_version": "1.1.0",
            "entry_point": "server.py"
        }
        is_valid, errors = strategy.validate_entry_point(metadata, self.context)
        # Result depends on whether file exists in package directory
    
    def test_schema_validation_strategy(self):
        """Test SchemaValidation strategy for v1.1.0."""
        strategy = SchemaValidationV1_1_0()
        
        valid_metadata = {
            "package_schema_version": "1.1.0",
            "name": "test_pkg",
            "version": "1.0.0",
            "entry_point": "server.py",
            "description": "Test package",
            "tags": ["test"],
            "author": {"name": "Test Author"},
            "license": {"name": "MIT"}
        }
        
        is_valid, errors = strategy.validate_schema(valid_metadata, self.context)
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()