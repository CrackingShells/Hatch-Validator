"""Unit tests for v2.0.0 package validator specific features.

Tests behavioral differences introduced by v2.0.0:
- authors is an array (v1.x had a single author object)
- Validator and accessor routing for schema version "2.0.0"
"""

import unittest

from hatch_validator.core.validator_factory import ValidatorFactory
from hatch_validator.core.pkg_accessor_factory import HatchPkgAccessorFactory
from hatch_validator.package.package_service import PackageService


class TestPackageValidatorV200(unittest.TestCase):
    """Unit tests for v2.0.0 specific validation features."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ValidatorFactory.create_validator_chain("2.0.0")
        self.accessor = HatchPkgAccessorFactory.create_accessor_chain("2.0.0")

    def test_authors_array_access(self):
        """Test that authors field returns an array in v2.0.0."""
        metadata = {
            "hatch_schema_version": "2.0.0",
            "name": "test-package",
            "authors": [
                {"name": "Author One", "email": "one@example.com"},
                {"name": "Author Two", "email": "two@example.com"}
            ]
        }

        service = PackageService()
        service.load_metadata(metadata)
        authors = service.get_field("author")
        self.assertIsInstance(authors, list)
        self.assertEqual(len(authors), 2)
        self.assertEqual(authors[0]["name"], "Author One")
        self.assertEqual(authors[1]["name"], "Author Two")

    def test_v2_0_0_validator_can_handle(self):
        """Test that v2.0.0 validator correctly identifies supported versions."""
        self.assertTrue(self.validator.can_handle("2.0.0"))
        self.assertFalse(self.validator.can_handle("1.2.2"))
        self.assertFalse(self.validator.can_handle("3.0.0"))

    def test_v2_0_0_accessor_can_handle(self):
        """Test that v2.0.0 accessor correctly identifies supported versions."""
        self.assertTrue(self.accessor.can_handle("2.0.0"))
        self.assertFalse(self.accessor.can_handle("1.2.2"))
        self.assertFalse(self.accessor.can_handle("3.0.0"))


if __name__ == "__main__":
    unittest.main()
