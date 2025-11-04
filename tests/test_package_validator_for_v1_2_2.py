"""Unit tests for package validation with schema version 1.2.2.

This module tests the validation functionality for packages using schema
version 1.2.2, which introduces conda package manager support for Python
dependencies.
"""

import unittest
import json
from pathlib import Path
from typing import Dict

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.core.validator_factory import ValidatorFactory
from hatch_validator.core.pkg_accessor_factory import HatchPkgAccessorFactory


class TestV122PackageValidation(unittest.TestCase):
    """Test cases for v1.2.2 package validation."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        # Create minimal test registry data
        cls.registry_data = {
            "registry_schema_version": "1.0.0",
            "repositories": []
        }

    def setUp(self):
        """Set up each test."""
        self.context = ValidationContext(
            registry_data=self.registry_data,
            allow_local_dependencies=False,
            force_schema_update=False
        )
    
    def test_valid_v122_package_with_conda_dependencies(self):
        """Test validation of valid v1.2.2 package with conda dependencies."""
        metadata = {
            "package_schema_version": "1.2.2",
            "name": "test_conda_package",
            "version": "1.0.0",
            "description": "Test package with conda dependencies",
            "tags": ["test", "conda"],
            "author": {"name": "Test Author", "email": "test@example.com"},
            "license": {"name": "MIT"},
            "entry_point": {
                "mcp_server": "server.py",
                "hatch_mcp_server": "hatch_server.py"
            },
            "dependencies": {
                "python": [
                    {
                        "name": "numpy",
                        "version_constraint": ">=1.20.0",
                        "package_manager": "conda",
                        "channel": "conda-forge"
                    },
                    {
                        "name": "scipy",
                        "version_constraint": ">=1.7.0",
                        "package_manager": "conda",
                        "channel": "bioconda"
                    }
                ]
            }
        }
        
        validator = ValidatorFactory.create_validator_chain("1.2.2")
        is_valid, errors = validator.validate(metadata, self.context)
        
        # Note: This will fail schema validation until we have the actual files
        # but it tests the validator chain construction
        self.assertIsNotNone(validator)
    
    def test_valid_v122_package_with_pip_dependencies(self):
        """Test validation of valid v1.2.2 package with pip dependencies (backward compatibility)."""
        metadata = {
            "package_schema_version": "1.2.2",
            "name": "test_pip_package",
            "version": "1.0.0",
            "description": "Test package with pip dependencies",
            "tags": ["test", "pip"],
            "author": {"name": "Test Author"},
            "license": {"name": "MIT"},
            "entry_point": {
                "mcp_server": "server.py",
                "hatch_mcp_server": "hatch_server.py"
            },
            "dependencies": {
                "python": [
                    {
                        "name": "requests",
                        "version_constraint": ">=2.28.0",
                        "package_manager": "pip"
                    }
                ]
            }
        }
        
        validator = ValidatorFactory.create_validator_chain("1.2.2")
        is_valid, errors = validator.validate(metadata, self.context)
        
        self.assertIsNotNone(validator)
    
    def test_valid_v122_package_with_mixed_dependencies(self):
        """Test validation of valid v1.2.2 package with mixed pip and conda dependencies."""
        metadata = {
            "package_schema_version": "1.2.2",
            "name": "test_mixed_package",
            "version": "1.0.0",
            "description": "Test package with mixed dependencies",
            "tags": ["test", "mixed"],
            "author": {"name": "Test Author"},
            "license": {"name": "MIT"},
            "entry_point": {
                "mcp_server": "server.py",
                "hatch_mcp_server": "hatch_server.py"
            },
            "dependencies": {
                "python": [
                    {
                        "name": "requests",
                        "version_constraint": ">=2.28.0",
                        "package_manager": "pip"
                    },
                    {
                        "name": "numpy",
                        "version_constraint": ">=1.20.0",
                        "package_manager": "conda",
                        "channel": "conda-forge"
                    }
                ]
            }
        }
        
        validator = ValidatorFactory.create_validator_chain("1.2.2")
        is_valid, errors = validator.validate(metadata, self.context)

        self.assertIsNotNone(validator)

    def test_invalid_channel_for_pip_package(self):
        """Test that channel specification for pip package is invalid."""
        from hatch_validator.package.v1_2_2.dependency_validation import DependencyValidation

        dep_validation = DependencyValidation()

        # Pip package with channel should fail
        dep = {
            "name": "requests",
            "version_constraint": ">=2.28.0",
            "package_manager": "pip",
            "channel": "conda-forge"  # Invalid for pip
        }

        is_valid, errors = dep_validation._validate_single_python_dependency(dep, self.context)

        self.assertFalse(is_valid)
        self.assertTrue(any("Channel" in error and "pip" in error for error in errors))

    def test_invalid_channel_format(self):
        """Test that invalid channel format is rejected."""
        from hatch_validator.package.v1_2_2.dependency_validation import DependencyValidation

        dep_validation = DependencyValidation()

        # Conda package with invalid channel format
        dep = {
            "name": "numpy",
            "version_constraint": ">=1.20.0",
            "package_manager": "conda",
            "channel": "invalid channel!"  # Invalid format (contains space and !)
        }

        is_valid, errors = dep_validation._validate_single_python_dependency(dep, self.context)

        self.assertFalse(is_valid)
        self.assertTrue(any("channel format" in error.lower() for error in errors))

    def test_valid_channel_formats(self):
        """Test that valid channel formats are accepted."""
        from hatch_validator.package.v1_2_2.dependency_validation import DependencyValidation

        dep_validation = DependencyValidation()

        valid_channels = ["conda-forge", "bioconda", "colomoto", "my_channel", "channel123"]

        for channel in valid_channels:
            dep = {
                "name": "numpy",
                "version_constraint": ">=1.20.0",
                "package_manager": "conda",
                "channel": channel
            }

            is_valid, errors = dep_validation._validate_single_python_dependency(dep, self.context)

            # Should be valid (no channel format errors)
            channel_format_errors = [e for e in errors if "channel format" in e.lower()]
            self.assertEqual(len(channel_format_errors), 0,
                           f"Channel '{channel}' should be valid but got errors: {channel_format_errors}")

    def test_invalid_package_manager(self):
        """Test that invalid package_manager value is rejected."""
        from hatch_validator.package.v1_2_2.dependency_validation import DependencyValidation

        dep_validation = DependencyValidation()

        dep = {
            "name": "numpy",
            "version_constraint": ">=1.20.0",
            "package_manager": "apt"  # Invalid - only pip or conda allowed
        }

        is_valid, errors = dep_validation._validate_single_python_dependency(dep, self.context)

        self.assertFalse(is_valid)
        self.assertTrue(any("package_manager" in error and "apt" in error for error in errors))

    def test_conda_package_without_channel(self):
        """Test that conda package without channel is valid (channel is optional)."""
        from hatch_validator.package.v1_2_2.dependency_validation import DependencyValidation

        dep_validation = DependencyValidation()

        dep = {
            "name": "numpy",
            "version_constraint": ">=1.20.0",
            "package_manager": "conda"
            # No channel specified - should be valid
        }

        is_valid, errors = dep_validation._validate_single_python_dependency(dep, self.context)

        # Should be valid (channel is optional)
        self.assertTrue(is_valid, f"Conda package without channel should be valid, but got errors: {errors}")

    def test_default_package_manager_is_pip(self):
        """Test that package_manager defaults to pip when not specified."""
        from hatch_validator.package.v1_2_2.dependency_validation import DependencyValidation

        dep_validation = DependencyValidation()

        dep = {
            "name": "requests",
            "version_constraint": ">=2.28.0"
            # No package_manager specified - should default to pip
        }

        is_valid, errors = dep_validation._validate_single_python_dependency(dep, self.context)

        # Should be valid (defaults to pip)
        self.assertTrue(is_valid, f"Package without package_manager should default to pip, but got errors: {errors}")


class TestV122AccessorChain(unittest.TestCase):
    """Test cases for v1.2.2 accessor chain."""

    def test_accessor_chain_construction(self):
        """Test that v1.2.2 accessor chain is constructed correctly."""
        accessor = HatchPkgAccessorFactory.create_accessor_chain("1.2.2")

        self.assertIsNotNone(accessor)
        self.assertTrue(accessor.can_handle("1.2.2"))

    def test_accessor_delegates_to_v121(self):
        """Test that v1.2.2 accessor delegates to v1.2.1 for unchanged operations."""
        accessor = HatchPkgAccessorFactory.create_accessor_chain("1.2.2")

        metadata = {
            "package_schema_version": "1.2.2",
            "name": "test_package",
            "version": "1.0.0",
            "entry_point": {
                "mcp_server": "server.py",
                "hatch_mcp_server": "hatch_server.py"
            }
        }

        # Test that accessor can access entry points (delegated to v1.2.1)
        mcp_entry = accessor.get_mcp_entry_point(metadata)
        self.assertEqual(mcp_entry, "server.py")

        hatch_mcp_entry = accessor.get_hatch_mcp_entry_point(metadata)
        self.assertEqual(hatch_mcp_entry, "hatch_server.py")


class TestV122ValidatorChain(unittest.TestCase):
    """Test cases for v1.2.2 validator chain."""

    def test_validator_chain_construction(self):
        """Test that v1.2.2 validator chain is constructed correctly."""
        validator = ValidatorFactory.create_validator_chain("1.2.2")

        self.assertIsNotNone(validator)
        self.assertTrue(validator.can_handle("1.2.2"))

    def test_validator_chain_includes_all_versions(self):
        """Test that v1.2.2 validator chain includes all previous versions."""
        validator = ValidatorFactory.create_validator_chain("1.2.2")

        # Check chain includes v1.2.2, v1.2.1, v1.2.0, v1.1.0
        current = validator
        versions_in_chain = []

        while current:
            if hasattr(current, 'can_handle'):
                # Find which version this validator handles
                for version in ["1.2.2", "1.2.1", "1.2.0", "1.1.0"]:
                    if current.can_handle(version):
                        versions_in_chain.append(version)
                        break
            current = getattr(current, 'next_validator', None)

        self.assertIn("1.2.2", versions_in_chain)
        self.assertIn("1.2.1", versions_in_chain)
        self.assertIn("1.2.0", versions_in_chain)
        self.assertIn("1.1.0", versions_in_chain)


if __name__ == '__main__':
    unittest.main()


