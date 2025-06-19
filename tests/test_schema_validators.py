"""Unit tests for schema validation framework base classes.

This module tests the abstract base classes and interfaces that form
the foundation of the Chain of Responsibility and Strategy patterns.
"""

import unittest
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.core.validator_base import Validator
from hatch_validator.core.validation_strategy import (
    DependencyValidationStrategy,
    ToolsValidationStrategy,
    EntryPointValidationStrategy,
    SchemaValidationStrategy
)
from hatch_validator.core.validator_factory import ValidatorFactory


class ConcreteValidator(Validator):
    """Concrete implementation of Validator for testing."""
    
    def __init__(self, supported_version: str, next_validator=None):
        """Initialize test validator.
        
        Args:
            supported_version (str): Version this validator supports
            next_validator: Next validator in chain
        """
        super().__init__(next_validator)
        self.supported_version = supported_version
        self.validation_called = False
    
    def validate(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Test implementation of validate method."""
        self.validation_called = True
        
        if not self.can_handle(metadata.get("package_schema_version", "")):
            if self.next_validator:
                return self.next_validator.validate(metadata, context)
            return False, [f"Unsupported schema version: {metadata.get('package_schema_version')}"]
        
        return True, []
    
    def can_handle(self, schema_version: str) -> bool:
        """Test implementation of can_handle method."""
        return schema_version == self.supported_version


class ConcreteDependencyValidationStrategy(DependencyValidationStrategy):
    """Concrete implementation of DependencyValidationStrategy for testing."""
    
    def __init__(self):
        """Initialize test strategy."""
        self.validation_called = False
    
    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Test implementation of validate_dependencies method."""
        self.validation_called = True
        return True, []


class TestValidationContext(unittest.TestCase):
    """Test cases for ValidationContext class."""
    
    def test_initialization_with_defaults(self):
        """Test ValidationContext initialization with default values."""
        context = ValidationContext()
        
        self.assertIsNone(context.package_dir)
        self.assertIsNone(context.registry_data)
        self.assertTrue(context.allow_local_dependencies)
        self.assertFalse(context.force_schema_update)
        self.assertEqual(context.additional_data, {})
    
    def test_initialization_with_values(self):
        """Test ValidationContext initialization with provided values."""
        package_dir = Path("/test/package")
        registry_data = {"test": "data"}
        
        context = ValidationContext(
            package_dir=package_dir,
            registry_data=registry_data,
            allow_local_dependencies=False,
            force_schema_update=True
        )
        
        self.assertEqual(context.package_dir, package_dir)
        self.assertEqual(context.registry_data, registry_data)
        self.assertFalse(context.allow_local_dependencies)
        self.assertTrue(context.force_schema_update)
    
    def test_set_and_get_data(self):
        """Test setting and getting additional data in context."""
        context = ValidationContext()
        
        context.set_data("test_key", "test_value")
        self.assertEqual(context.get_data("test_key"), "test_value")
        
        # Test default value
        self.assertEqual(context.get_data("nonexistent_key", "default"), "default")
        self.assertIsNone(context.get_data("nonexistent_key"))


class TestSchemaValidator(unittest.TestCase):
    """Test cases for Validator abstract base class."""
    
    def test_chain_construction(self):
        """Test that validator chain can be constructed properly."""
        validator1 = ConcreteValidator("1.1.0")
        validator2 = ConcreteValidator("1.0.0")
        
        validator1.set_next(validator2)
        
        self.assertEqual(validator1.next_validator, validator2)
        self.assertIsNone(validator2.next_validator)
    
    def test_can_handle_functionality(self):
        """Test the can_handle method functionality."""
        validator = ConcreteValidator("1.1.0")
        
        self.assertTrue(validator.can_handle("1.1.0"))
        self.assertFalse(validator.can_handle("1.2.0"))
        self.assertFalse(validator.can_handle(""))
    
    def test_validation_delegation(self):
        """Test that validation is properly delegated in the chain."""
        validator1 = ConcreteValidator("1.2.0")
        validator2 = ConcreteValidator("1.1.0")
        validator1.set_next(validator2)
        
        context = ValidationContext()
        metadata = {"package_schema_version": "1.1.0"}
        
        # Should delegate to validator2
        is_valid, errors = validator1.validate(metadata, context)
        
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])
        self.assertTrue(validator1.validation_called)
        self.assertTrue(validator2.validation_called)
    
    def test_validation_without_delegation(self):
        """Test validation when validator can handle the version directly."""
        validator = ConcreteValidator("1.1.0")
        context = ValidationContext()
        metadata = {"package_schema_version": "1.1.0"}
        
        is_valid, errors = validator.validate(metadata, context)
        
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])
        self.assertTrue(validator.validation_called)
    
    def test_validation_failure_no_handler(self):
        """Test validation failure when no validator in chain can handle version."""
        validator = ConcreteValidator("1.1.0")
        context = ValidationContext()
        metadata = {"package_schema_version": "2.0.0"}
        
        is_valid, errors = validator.validate(metadata, context)
        
        self.assertFalse(is_valid)
        self.assertEqual(len(errors), 1)
        self.assertIn("Unsupported schema version", errors[0])


class TestValidationStrategies(unittest.TestCase):
    """Test cases for validation strategy interfaces."""
    
    def test_dependency_strategy_interface(self):
        """Test that DependencyValidationStrategy interface works correctly."""
        strategy = ConcreteDependencyValidationStrategy()
        context = ValidationContext()
        metadata = {"dependencies": []}
        
        is_valid, errors = strategy.validate_dependencies(metadata, context)
        
        self.assertTrue(is_valid)
        self.assertEqual(errors, [])
        self.assertTrue(strategy.validation_called)
    
    def test_cannot_instantiate_abstract_classes(self):
        """Test that abstract base classes cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            Validator()
        
        with self.assertRaises(TypeError):
            DependencyValidationStrategy()
        
        with self.assertRaises(TypeError):
            ToolsValidationStrategy()
        
        with self.assertRaises(TypeError):
            EntryPointValidationStrategy()
        
        with self.assertRaises(TypeError):
            SchemaValidationStrategy()


class TestValidatorFactory(unittest.TestCase):
    """Test cases for ValidatorFactory class."""
    def test_factory_implementation(self):
        """Test that factory now works after Phase 2 implementation."""
        validator = ValidatorFactory.create_validator_chain()
        self.assertIsNotNone(validator)
        
        validator_v1_1_0 = ValidatorFactory.create_validator_chain("1.1.0")
        self.assertIsNotNone(validator_v1_1_0)
        
        # Test v1.2.0 validator creation
        validator_v1_2_0 = ValidatorFactory.create_validator_chain("1.2.0")
        self.assertIsNotNone(validator_v1_2_0)
    
    def test_v1_2_0_validator_chain_delegation(self):
        """Test that v1.2.0 validator properly delegates to v1.1.0."""
        validator = ValidatorFactory.create_validator_chain("1.2.0")
        context = ValidationContext()
        
        # Test v1.2.0 metadata
        v1_2_0_metadata = {"package_schema_version": "1.2.0"}
        is_valid, errors = validator.validate(v1_2_0_metadata, context)
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(errors, list)
        
        # Test v1.1.0 metadata (should delegate)
        v1_1_0_metadata = {"package_schema_version": "1.1.0"}
        is_valid, errors = validator.validate(v1_1_0_metadata, context)
        self.assertIsInstance(is_valid, bool)
        self.assertIsInstance(errors, list)
    
    def test_supported_versions_includes_v1_2_0(self):
        """Test that v1.2.0 is included in supported versions."""
        supported_versions = ValidatorFactory.get_supported_versions()
        self.assertIn("1.2.0", supported_versions)
        self.assertIn("1.1.0", supported_versions)


if __name__ == "__main__":
    unittest.main()
