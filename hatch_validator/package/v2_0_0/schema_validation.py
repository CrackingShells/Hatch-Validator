"""Schema validation strategy for v2.0.0.

This module provides the schema validation strategy for schema version 2.0.0.
"""

import logging
from typing import Dict, List, Tuple

from hatch_validator.core.validation_strategy import SchemaValidationStrategy
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.schemas.schemas_retriever import get_package_schema

# Configure logging
logger = logging.getLogger("hatch.schema.v2_0_0.schema_validation")


class SchemaValidation(SchemaValidationStrategy):
    """Strategy for validating metadata against v2.0.0 schema."""

    def validate_schema(
        self, metadata: Dict, context: ValidationContext
    ) -> Tuple[bool, List[str]]:
        """Validate metadata against v2.0.0 schema.

        Args:
            metadata (Dict): Package metadata to validate against schema
            context (ValidationContext): Validation context with resources

        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether schema validation was successful
                - List[str]: List of schema validation errors
        """
        try:
            jsonschema = __import__("jsonschema")
        except ImportError:
            error_msg = (
                "jsonschema is required for schema validation but is not installed"
            )
            logger.error(error_msg)
            return False, [error_msg]

        try:
            schema = get_package_schema(
                version="2.0.0", force_update=context.force_schema_update
            )
            if not schema:
                error_msg = "Failed to load package schema version 2.0.0"
                logger.error(error_msg)
                return False, [error_msg]

            jsonschema.validate(instance=metadata, schema=schema)
            logger.debug(
                "Package metadata successfully validated against v2.0.0 schema"
            )
            return True, []

        except jsonschema.ValidationError as e:
            error_msg = f"Schema validation failed: {e.message}"
            if e.absolute_path:
                error_msg += f" at path: {'.'.join(str(p) for p in e.absolute_path)}"
            logger.error(error_msg)
            return False, [error_msg]
        except Exception as e:
            error_msg = f"Unexpected error during schema validation: {str(e)}"
            logger.error(error_msg)
            return False, [error_msg]
