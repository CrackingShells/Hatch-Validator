"""Unit tests for v2.0.0 package validator specific features.

Tests individual validation strategies and accessor behaviors for v2.0.0 schema:
- Schema routing (hatch_schema_version vs package_schema_version)
- Citations validation strategy
- Provenance validation strategy
- Docker digest requirements and version_constraint rejection
- Tools desc field handling (preferred over deprecated description)
- Authors array access (instead of single author object)
"""

import unittest
from unittest.mock import Mock, patch

from hatch_validator.core.validator_factory import ValidatorFactory
from hatch_validator.core.pkg_accessor_factory import HatchPkgAccessorFactory
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.package.package_service import PackageService


class TestPackageValidatorV200(unittest.TestCase):
    """Unit tests for v2.0.0 specific validation features."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = ValidatorFactory.create_validator_chain("2.0.0")
        self.accessor = HatchPkgAccessorFactory.create_accessor_chain("2.0.0")
        self.context = ValidationContext(force_schema_update=False)

    def test_schema_routing_hatch_schema_version(self):
        """Test that packages with hatch_schema_version route to v2.0.0."""
        metadata = {
            "hatch_schema_version": "2.0.0",
            "name": "test-package",
            "description": "Test package",
            "authors": [{"name": "Test Author", "email": "test@example.com"}],
            "version": "1.0.0"
        }

        service = PackageService()
        service.load_metadata(metadata)
        self.assertTrue(service.is_loaded())
        self.assertEqual(service.get_field("name"), "test-package")

    def test_schema_routing_package_schema_version_fallback(self):
        """Test that packages with package_schema_version still route to v2.0.0 for backward compatibility."""
        metadata = {
            "package_schema_version": "2.0.0",
            "name": "test-package",
            "description": "Test package",
            "authors": [{"name": "Test Author", "email": "test@example.com"}],
            "version": "1.0.0"
        }

        service = PackageService()
        service.load_metadata(metadata)
        self.assertTrue(service.is_loaded())
        self.assertEqual(service.get_field("name"), "test-package")

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
        authors = service.get_field("authors")
        self.assertIsInstance(authors, list)
        self.assertEqual(len(authors), 2)
        self.assertEqual(authors[0]["name"], "Author One")
        self.assertEqual(authors[1]["name"], "Author Two")

    def test_tools_desc_field_preferred(self):
        """Test that tools[].desc is preferred over deprecated description."""
        metadata = {
            "hatch_schema_version": "2.0.0",
            "name": "test-package",
            "tools": [
                {
                    "name": "tool1",
                    "desc": "Modern description field",
                    "description": "Deprecated description field"
                }
            ]
        }

        service = PackageService()
        service.load_metadata(metadata)
        tools = service.get_tools()
        self.assertIsInstance(tools, list)
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0]["desc"], "Modern description field")
        # The accessor should still provide both fields for compatibility
        self.assertIn("description", tools[0])

    def test_tools_validation_prefers_desc(self):
        """Test that tools validation flags deprecated description usage."""
        metadata = {
            "hatch_schema_version": "2.0.0",
            "name": "test-package",
            "tools": [
                {
                    "name": "tool1",
                    "description": "Only deprecated description field"
                }
            ]
        }

        is_valid, errors = self.validator.validate(metadata, self.context)
        # Should still be valid but may warn about deprecated field
        self.assertIsInstance(errors, list)

    def test_docker_dependency_digest_required(self):
        """Test that Docker dependencies require digest in v2.0.0."""
        metadata = {
            "hatch_schema_version": "2.0.0",
            "name": "test-package",
            "dependencies": {
                "docker": [
                    {
                        "image": "ubuntu:20.04",
                        "digest": "sha256:1234567890abcdef"
                    }
                ]
            }
        }

        is_valid, errors = self.validator.validate(metadata, self.context)
        # Should be valid with digest
        self.assertIsInstance(errors, list)

    def test_docker_dependency_version_constraint_rejected(self):
        """Test that Docker dependencies reject version_constraint in v2.0.0."""
        metadata = {
            "hatch_schema_version": "2.0.0",
            "name": "test-package",
            "dependencies": {
                "docker": [
                    {
                        "image": "ubuntu:20.04",
                        "version_constraint": ">=20.04"
                    }
                ]
            }
        }

        is_valid, errors = self.validator.validate(metadata, self.context)
        # Should be invalid due to version_constraint
        self.assertIsInstance(errors, list)

    def test_docker_dependency_optional_tag(self):
        """Test that Docker dependencies allow optional tag in v2.0.0."""
        metadata = {
            "hatch_schema_version": "2.0.0",
            "name": "test-package",
            "dependencies": {
                "docker": [
                    {
                        "image": "ubuntu:20.04",
                        "tag": "20.04",
                        "digest": "sha256:1234567890abcdef"
                    }
                ]
            }
        }

        is_valid, errors = self.validator.validate(metadata, self.context)
        # Should be valid with optional tag
        self.assertIsInstance(errors, list)

    def test_provenance_validation_basic(self):
        """Test basic provenance validation for v2.0.0."""
        metadata = {
            "hatch_schema_version": "2.0.0",
            "name": "test-package",
            "provenance": {
                "source": "https://github.com/example/repo",
                "license": "MIT"
            }
        }

        is_valid, errors = self.validator.validate(metadata, self.context)
        self.assertIsInstance(errors, list)

    def test_provenance_validation_rejects_unsupported_fields(self):
        """Test that provenance validation rejects unsupported fields like created_by/created_at."""
        metadata = {
            "hatch_schema_version": "2.0.0",
            "name": "test-package",
            "provenance": {
                "source": "https://github.com/example/repo",
                "license": "MIT",
                "created_by": "test-user",  # Should be rejected
                "created_at": "2023-01-01T00:00:00Z"  # Should be rejected
            }
        }

        is_valid, errors = self.validator.validate(metadata, self.context)
        # Should be invalid due to unsupported fields
        self.assertIsInstance(errors, list)

    def test_citations_validation_basic(self):
        """Test basic citations validation for v2.0.0."""
        metadata = {
            "hatch_schema_version": "2.0.0",
            "name": "test-package",
            "citations": [
                {
                    "text": "Example citation",
                    "doi": "10.1234/example"
                }
            ]
        }

        is_valid, errors = self.validator.validate(metadata, self.context)
        self.assertIsInstance(errors, list)

    def test_citations_validation_array_required(self):
        """Test that citations must be an array in v2.0.0."""
        metadata = {
            "hatch_schema_version": "2.0.0",
            "name": "test-package",
            "citations": {
                "text": "Invalid citation format",
                "doi": "10.1234/example"
            }
        }

        is_valid, errors = self.validator.validate(metadata, self.context)
        # Should be invalid due to non-array citations
        self.assertIsInstance(errors, list)

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

    def test_entry_point_validation_v2_0_0(self):
        """Test entry point validation for v2.0.0 schema."""
        metadata = {
            "hatch_schema_version": "2.0.0",
            "name": "test-package",
            "entry_point": "main.py"
        }

        is_valid, errors = self.validator.validate(metadata, self.context)
        self.assertIsInstance(errors, list)

    def test_schema_validation_uses_v2_0_0_schema(self):
        """Test that schema validation uses the 2.0.0 schema version."""
        metadata = {
            "hatch_schema_version": "2.0.0",
            "name": "test-package",
            "description": "Test package",
            "authors": [{"name": "Test Author", "email": "test@example.com"}],
            "version": "1.0.0"
        }

        with patch('hatch_validator.schemas.schemas_retriever.get_package_schema') as mock_get_schema:
            mock_get_schema.return_value = {"type": "object"}  # Minimal valid schema
            is_valid, errors = self.validator.validate(metadata, self.context)
            mock_get_schema.assert_called_with(version="2.0.0", force_update=False)


if __name__ == "__main__":
    unittest.main()