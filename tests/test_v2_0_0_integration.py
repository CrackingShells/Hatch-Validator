"""Integration test for v2.0.0 schema support.

This test demonstrates the full functionality of v2.0.0 schema validation
using official published examples from the Hatch-Schemas repository.
"""

import json
import unittest
from pathlib import Path

from hatch_validator.core.validator_factory import ValidatorFactory
from hatch_validator.core.pkg_accessor_factory import HatchPkgAccessorFactory
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.package.package_service import PackageService


class TestV200Integration(unittest.TestCase):
    """Integration tests for v2.0.0 schema support."""

    def setUp(self):
        """Set up test fixtures."""
        # Load official v2.0.0 examples
        self.valid_example = self._load_example("server_v2.0.0_example.json")
        self.invalid_example = self._load_example("server_v2.0.0_invalid_example.json")

    def _load_example(self, filename: str) -> dict:
        """Load example JSON from the Hatch-Schemas repository."""
        import urllib.request

        url = f"https://raw.githubusercontent.com/CrackingShells/Hatch-Schemas/main/examples/{filename}"
        try:
            with urllib.request.urlopen(url) as response:
                return json.loads(response.read().decode('utf-8'))
        except Exception as e:
            self.fail(f"Failed to load example {filename}: {e}")

    def test_v2_0_0_validator_chain_creation(self):
        """Test that v2.0.0 validator chain can be created."""
        validator = ValidatorFactory.create_validator_chain("2.0.0")
        self.assertIsNotNone(validator)
        self.assertTrue(validator.can_handle("2.0.0"))

    def test_v2_0_0_accessor_chain_creation(self):
        """Test that v2.0.0 accessor chain can be created."""
        accessor = HatchPkgAccessorFactory.create_accessor_chain("2.0.0")
        self.assertIsNotNone(accessor)
        self.assertTrue(accessor.can_handle("2.0.0"))

    def test_valid_v2_0_0_example_validation(self):
        """Test validation of the official valid v2.0.0 example."""
        validator = ValidatorFactory.create_validator_chain("2.0.0")
        context = ValidationContext(force_schema_update=False)

        is_valid, errors = validator.validate(self.valid_example, context)
        self.assertTrue(is_valid, f"Valid example should pass validation. Errors: {errors}")
        self.assertEqual(len(errors), 0, f"No errors expected for valid example. Errors: {errors}")

    def test_invalid_v2_0_0_example_validation(self):
        """Test validation of the official invalid v2.0.0 example."""
        validator = ValidatorFactory.create_validator_chain("2.0.0")
        context = ValidationContext(force_schema_update=False)

        is_valid, errors = validator.validate(self.invalid_example, context)
        self.assertFalse(is_valid, "Invalid example should fail validation")
        self.assertGreater(len(errors), 0, "Invalid example should produce errors")

    def test_v2_0_0_package_service_with_valid_example(self):
        """Test PackageService with the official valid v2.0.0 example."""
        service = PackageService()
        service.load_metadata(self.valid_example)

        # Test basic field access
        self.assertEqual(service.get_field("name"), self.valid_example.get("name"))
        self.assertEqual(service.get_field("description"), self.valid_example.get("description"))

        # Test authors array (v2.0.0 specific)
        authors = service.get_field("authors")
        self.assertIsInstance(authors, list)
        self.assertGreater(len(authors), 0)

        # Test tools with desc field (v2.0.0 specific)
        tools = service.get_tools()
        if tools:
            for tool in tools:
                if "desc" in tool:
                    self.assertIsInstance(tool["desc"], str)

        # Test dependencies (should include Docker with digest)
        dependencies = service.get_dependencies()
        self.assertIsInstance(dependencies, dict)

    def test_v2_0_0_package_service_with_invalid_example(self):
        """Test PackageService with the official invalid v2.0.0 example."""
        service = PackageService()
        # Invalid example should still load (service doesn't validate, just accesses)
        service.load_metadata(self.invalid_example)

        # Basic access should still work
        self.assertEqual(service.get_field("name"), self.invalid_example.get("name"))

    def test_v2_0_0_schema_routing(self):
        """Test that v2.0.0 packages route correctly based on hatch_schema_version."""
        # Test with hatch_schema_version
        metadata_with_hatch = self.valid_example.copy()
        metadata_with_hatch["hatch_schema_version"] = "2.0.0"

        service = PackageService()
        service.load_metadata(metadata_with_hatch)
        self.assertTrue(service.is_loaded())

        # Test with package_schema_version (backward compatibility)
        metadata_with_package = self.valid_example.copy()
        metadata_with_package["package_schema_version"] = "2.0.0"
        if "hatch_schema_version" in metadata_with_package:
            del metadata_with_package["hatch_schema_version"]

        service2 = PackageService()
        service2.load_metadata(metadata_with_package)
        self.assertTrue(service2.is_loaded())


if __name__ == "__main__":
    unittest.main()