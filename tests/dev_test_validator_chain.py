"""Developer tests for the enhanced Chain of Responsibility implementation.

This module contains tests for the enhanced Chain of Responsibility pattern
with delegated validation methods.
"""

import unittest
from unittest.mock import Mock, patch
from pathlib import Path
import sys
import os
import logging
import json
from datetime import datetime

# Add parent directory to path to allow importing from hatch_validator
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hatch_validator.core.validator_base import SchemaValidator
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.core.validator_factory import ValidatorFactory
from hatch_validator.schemas.v1_1_0.schema_validators import SchemaValidator as V110Validator
from hatch_validator.utils.registry_client import DirectRegistryClient, RegistryManager

# Configure logging
logger = logging.getLogger("hatch.dev_tests.validator_chain")


class TestValidatorEnhancements(unittest.TestCase):
    """Tests for the enhanced validator chain functionality."""

    def setUp(self):
        """Set up test fixtures."""

        # Path to Hatch-Dev packages
        self.hatch_dev_path = Path(__file__).parent.parent.parent / "Hatching-Dev"
        self.assertTrue(self.hatch_dev_path.exists(), 
                        f"Hatch-Dev directory not found at {self.hatch_dev_path}")


        # Build registry data structure from Hatch-Dev packages
        self.registry_data = self._build_test_registry()

        drc = DirectRegistryClient(registry_data=self.registry_data)
        RegistryManager(drc)
        
        # Create a mock context
        self.context = ValidationContext(
            package_dir=Path('/fake/path'),
            registry_data=self.registry_data,
            allow_local_dependencies=True
        )
        
        # Sample metadata
        self.metadata = {
            "package_schema_version": "1.1.0",
            "name": "test-package",
            "version": "1.0.0",
            "entry_point": "main.py",
            "tools": [
                {"name": "test_tool", "description": "A test tool"}
            ]
        }
        
        logger.info("Setting up validator enhancement tests")

    def _build_test_registry(self):
        """
        Build a test registry data structure from Hatch-Dev packages for dependency testing.
        This simulates the structure that would be expected from a real registry file.

        NOTE: Not actually used in the tests, but required to create a valid
        registry structure for the validator to work with.
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
        pkg_names = [
            "arithmetic_pkg", 
            "base_pkg_1", 
            "base_pkg_2", 
            "python_dep_pkg",
            "circular_dep_pkg_1",
            "circular_dep_pkg_2",
            "complex_dep_pkg",
            "simple_dep_pkg",
            "missing_dep_pkg",
            "version_dep_pkg"
        ]
        
        # Add each package to the registry
        for pkg_name in pkg_names:
            pkg_path = self.hatch_dev_path / pkg_name
            if pkg_path.exists():
                metadata_path = pkg_path / "hatch_metadata.json"
                if metadata_path.exists():
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            
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
                                        "hatch_dependencies_added": [
                                            {
                                                "name": dep["name"],
                                                "version_constraint": dep.get("version_constraint", "")
                                            }
                                            for dep in metadata.get("hatch_dependencies", [])
                                        ],
                                        "python_dependencies_added": [
                                            {
                                                "name": dep["name"],
                                                "version_constraint": dep.get("version_constraint", ""),
                                                "package_manager": dep.get("package_manager", "pip")
                                            }
                                            for dep in metadata.get("python_dependencies", [])
                                        ],
                                    }
                                ]
                            }
                            
                            # Add to registry
                            registry["repositories"][0]["packages"].append(pkg_entry)
                    except Exception as e:
                        logger.warning(f"Failed to load metadata for {pkg_name}: {e}")

        return registry
        
    def test_base_validator_delegation(self):
        """Test that the base validator properly delegates to next validator."""
        logger.info("Testing base validator delegation...")
        
        # Create a concrete mock subclass of SchemaValidator
        class MockValidator(SchemaValidator):
            def can_handle(self, schema_version):
                return schema_version == "mock"
                
            def validate(self, metadata, context):
                return True, []
                
            # Only implement one method, let others delegate
            def validate_schema(self, metadata, context):
                return True, ["Mock schema validation"]
        
        # Create a mock next validator
        mock_next = Mock(spec=SchemaValidator)
        mock_next.validate_dependencies.return_value = (True, ["Delegated dependency validation"])
        mock_next.validate_entry_point.return_value = (True, ["Delegated entry point validation"])
        mock_next.validate_tools.return_value = (True, ["Delegated tools validation"])
        
        # Create validator with the mock next validator
        validator = MockValidator(mock_next)
        
        # Test schema validation (not delegated)
        result, errors = validator.validate_schema({}, self.context)
        self.assertTrue(result)
        self.assertEqual(errors, ["Mock schema validation"])
        
        # Test dependency validation (delegated)
        result, errors = validator.validate_dependencies({}, self.context)
        self.assertTrue(result)
        self.assertEqual(errors, ["Delegated dependency validation"])
        mock_next.validate_dependencies.assert_called_once()
        
        # Test entry point validation (delegated)
        result, errors = validator.validate_entry_point({}, self.context)
        self.assertTrue(result)
        self.assertEqual(errors, ["Delegated entry point validation"])
        mock_next.validate_entry_point.assert_called_once()
        
        # Test tools validation (delegated)
        result, errors = validator.validate_tools({}, self.context)
        self.assertTrue(result)
        self.assertEqual(errors, ["Delegated tools validation"])
        mock_next.validate_tools.assert_called_once()
        
        logger.info("Base validator delegation tests passed")
        
    def test_validator_no_next_raises(self):
        """Test that validators without next implementation raise NotImplementedError."""
        logger.info("Testing NotImplementedError when no next validator...")
        
        # Create a concrete mock subclass of SchemaValidator with no next validator
        class MockValidator(SchemaValidator):
            def can_handle(self, schema_version):
                return schema_version == "mock"
                
            def validate(self, metadata, context):
                return True, []
                
            # Only implement one method, others should raise NotImplementedError
            def validate_schema(self, metadata, context):
                return True, ["Mock schema validation"]
        
        # Create validator with no next validator
        validator = MockValidator(None)
        
        # Test schema validation (implemented)
        result, errors = validator.validate_schema({}, self.context)
        self.assertTrue(result)
        self.assertEqual(errors, ["Mock schema validation"])
        
        # Test dependency validation (not implemented, should raise)
        with self.assertRaises(NotImplementedError):
            validator.validate_dependencies({}, self.context)
            
        # Test entry point validation (not implemented, should raise)
        with self.assertRaises(NotImplementedError):
            validator.validate_entry_point({}, self.context)
            
        # Test tools validation (not implemented, should raise)
        with self.assertRaises(NotImplementedError):
            validator.validate_tools({}, self.context)
            
        logger.info("NotImplementedError tests passed")
    
    def test_v110_validator_implementation(self):
        """Test that the v1.1.0 validator implements all required methods."""
        logger.info("Testing v1.1.0 validator implementation...")
        
        # Create a mock for DependencyValidationV1_1_0
        with patch('hatch_validator.schemas.v1_1_0.schema_validators.DependencyValidationV1_1_0') as mock_dep_class:
            # Set up the mock
            mock_dep_instance = Mock()
            mock_dep_instance.validate_dependencies.return_value = (True, ["Dependencies OK"])
            mock_dep_class.return_value = mock_dep_instance
            
            # Create v1.1.0 validator without next in chain
            validator = V110Validator(None)
            
            # Mock the other strategy methods to avoid actual validation
            validator.schema_strategy.validate_schema = Mock(return_value=(True, ["Schema OK"]))
            validator.entry_point_strategy.validate_entry_point = Mock(return_value=(True, ["Entry point OK"]))
            validator.tools_strategy.validate_tools = Mock(return_value=(True, ["Tools OK"]))
        
        # Test all validation methods
        schema_result, schema_errors = validator.validate_schema(self.metadata, self.context)
        self.assertTrue(schema_result)
        self.assertEqual(schema_errors, ["Schema OK"])
        
        deps_result, deps_errors = validator.validate_dependencies(self.metadata, self.context)
        self.assertTrue(deps_result)
        self.assertEqual(deps_errors, ["Dependencies OK"])
        
        entry_result, entry_errors = validator.validate_entry_point(self.metadata, self.context)
        self.assertTrue(entry_result)
        self.assertEqual(entry_errors, ["Entry point OK"])
        
        tools_result, tools_errors = validator.validate_tools(self.metadata, self.context)
        self.assertTrue(tools_result)
        self.assertEqual(tools_errors, ["Tools OK"])
        
        logger.info("v1.1.0 validator implementation tests passed")


if __name__ == '__main__':
    # Configure logging when running directly
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    unittest.main(verbosity=2)
