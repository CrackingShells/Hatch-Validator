"""Schema validation strategy for v1.2.2.

This module provides the schema validation strategy for schema version 1.2.2,
which validates packages with conda package manager support for Python dependencies.
"""

import logging
from typing import Dict, List, Tuple

import jsonschema

from hatch_validator.core.validation_strategy import SchemaValidationStrategy
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.schemas.schemas_retriever import get_package_schema


# Configure logging
logger = logging.getLogger("hatch.schema.v1_2_2.schema_validation")


class SchemaValidation(SchemaValidationStrategy):
    """Strategy for validating metadata against v1.2.2 schema.

    This strategy validates packages against the v1.2.2 schema which introduces
    conda package manager support for Python dependencies.
    """

    def validate_schema(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata against v1.2.2 schema.

        Args:
            metadata (Dict): Package metadata to validate against schema
            context (ValidationContext): Validation context with resources

        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether schema validation was successful
                - List[str]: List of schema validation errors
        """
        try:
            # Load schema for v1.2.2
            schema = get_package_schema(version="1.2.2", force_update=context.force_schema_update)
            if not schema:
                error_msg = "Failed to load package schema version 1.2.2"
                logger.error(error_msg)
                return False, [error_msg]

            # Validate against schema
            jsonschema.validate(instance=metadata, schema=schema)
            logger.debug("Package metadata successfully validated against v1.2.2 schema")
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

