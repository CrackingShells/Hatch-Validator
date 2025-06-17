"""Developer tests for the enhanced ValidatorFactory.

This module contains tests for the ValidatorFactory implementation
that supports proper Chain of Responsibility pattern construction.
"""

import unittest
from unittest.mock import Mock, patch
import logging
import sys
import os

# Add parent directory to path to allow importing from hatch_validator
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hatch_validator.core.validator_factory import ValidatorFactory
from hatch_validator.core.validator_base import SchemaValidator

# Configure logging
logger = logging.getLogger("hatch.dev_tests.validator_factory")


class MockValidatorV110(SchemaValidator):
    """Mock validator for v1.1.0 testing."""
    
    def can_handle(self, schema_version: str) -> bool:
        return schema_version == "1.1.0"
        
    def validate(self, metadata, context):
        return True, ["Mock v1.1.0 validation"]


class MockValidatorV120(SchemaValidator):
    """Mock validator for v1.2.0 testing."""
    
    def can_handle(self, schema_version: str) -> bool:
        return schema_version == "1.2.0"
        
    def validate(self, metadata, context):
        return True, ["Mock v1.2.0 validation"]


class TestValidatorFactory(unittest.TestCase):
    """Tests for the enhanced ValidatorFactory functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear the factory registry to start fresh
        ValidatorFactory._validator_registry.clear()
        ValidatorFactory._version_order.clear()
        logger.info("Setting up validator factory tests")
        
    def tearDown(self):
        """Clean up after tests."""
        # Clear the factory registry
        ValidatorFactory._validator_registry.clear()
        ValidatorFactory._version_order.clear()
        
    def test_validator_registration(self):
        """Test validator registration functionality."""
        logger.info("Testing validator registration...")
        
        # Register validators
        ValidatorFactory.register_validator("1.1.0", MockValidatorV110)
        ValidatorFactory.register_validator("1.2.0", MockValidatorV120)
        
        # Check registry
        self.assertIn("1.1.0", ValidatorFactory._validator_registry)
        self.assertIn("1.2.0", ValidatorFactory._validator_registry)
        
        # Check version ordering (newest first)
        supported_versions = ValidatorFactory.get_supported_versions()
        self.assertEqual(supported_versions, ["1.2.0", "1.1.0"])
        
        logger.info("Validator registration tests passed")
        
    def test_chain_creation_single_validator(self):
        """Test chain creation with a single validator."""
        logger.info("Testing chain creation with single validator...")
        
        # Register single validator
        ValidatorFactory.register_validator("1.1.0", MockValidatorV110)
        
        # Create chain
        chain_head = ValidatorFactory.create_validator_chain("1.1.0")
        
        # Verify chain structure
        self.assertIsInstance(chain_head, MockValidatorV110)
        self.assertIsNone(chain_head.next_validator)
        
        logger.info("Single validator chain creation tests passed")
        
    def test_chain_creation_multiple_validators(self):
        """Test chain creation with multiple validators."""
        logger.info("Testing chain creation with multiple validators...")
        
        # Register multiple validators
        ValidatorFactory.register_validator("1.1.0", MockValidatorV110)
        ValidatorFactory.register_validator("1.2.0", MockValidatorV120)
        
        # Create chain for latest version
        chain_head = ValidatorFactory.create_validator_chain()
        
        # Verify chain structure (v1.2.0 -> v1.1.0)
        self.assertIsInstance(chain_head, MockValidatorV120)
        self.assertIsNotNone(chain_head.next_validator)
        self.assertIsInstance(chain_head.next_validator, MockValidatorV110)
        self.assertIsNone(chain_head.next_validator.next_validator)
        
        logger.info("Multiple validator chain creation tests passed")
        
    def test_chain_creation_specific_version(self):
        """Test chain creation for a specific version."""
        logger.info("Testing chain creation for specific version...")
        
        # Register multiple validators
        ValidatorFactory.register_validator("1.1.0", MockValidatorV110)
        ValidatorFactory.register_validator("1.2.0", MockValidatorV120)
        
        # Create chain for v1.1.0 specifically
        chain_head = ValidatorFactory.create_validator_chain("1.1.0")
        
        # Verify chain structure (only v1.1.0)
        self.assertIsInstance(chain_head, MockValidatorV110)
        self.assertIsNone(chain_head.next_validator)
        
        logger.info("Specific version chain creation tests passed")
        
    def test_unsupported_version_error(self):
        """Test error handling for unsupported versions."""
        logger.info("Testing unsupported version error handling...")
        
        # Register validator
        ValidatorFactory.register_validator("1.1.0", MockValidatorV110)
        
        # Try to create chain for unsupported version
        with self.assertRaises(ValueError) as context:
            ValidatorFactory.create_validator_chain("2.0.0")
            
        self.assertIn("Unsupported schema version: 2.0.0", str(context.exception))
        
        logger.info("Unsupported version error handling tests passed")
    
    @patch('hatch_validator.core.validator_factory.ValidatorFactory._ensure_validators_loaded')
    def test_no_validators_error(self, mock_ensure_loaded):
        """Test error handling when no validators are available."""
        logger.info("Testing no validators error handling...")
        
        # Mock the ensure_validators_loaded to do nothing (no auto-loading)
        mock_ensure_loaded.return_value = None
        
        # Don't register any validators and ensure registry is empty
        ValidatorFactory._validator_registry.clear()
        ValidatorFactory._version_order.clear()
        
        # Try to create chain
        with self.assertRaises(ValueError) as context:
            ValidatorFactory.create_validator_chain()
            
        self.assertIn("No validators available", str(context.exception))
        
        logger.info("No validators error handling tests passed")
        
    @patch('hatch_validator.schemas.v1_1_0.schema_validators.SchemaValidator')
    def test_auto_loading_validators(self, mock_v110_validator):
        """Test automatic loading of available validators."""
        logger.info("Testing automatic validator loading...")
        
        # Mock the v1.1.0 validator class
        mock_v110_validator.return_value = MockValidatorV110()
        
        # Clear registry to force auto-loading
        ValidatorFactory._validator_registry.clear()
        ValidatorFactory._version_order.clear()
        
        # Create chain (should trigger auto-loading)
        chain_head = ValidatorFactory.create_validator_chain()
        
        # Verify v1.1.0 was registered
        supported_versions = ValidatorFactory.get_supported_versions()
        self.assertIn("1.1.0", supported_versions)
        
        logger.info("Automatic validator loading tests passed")


if __name__ == '__main__':
    # Configure logging when running directly
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    unittest.main(verbosity=2)
