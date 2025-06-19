"""Schema validation strategy for schema version v1.2.0.

This module implements schema validation against the v1.2.0 JSON schema.
"""

import logging
import jsonschema
from typing import Dict, List, Tuple

from hatch_validator.schemas.schemas_retriever import get_package_schema
from hatch_validator.core.validation_strategy import SchemaValidationStrategy
from hatch_validator.core.validation_context import ValidationContext

logger = logging.getLogger("hatch_validator.schemas.v1_2_0.schema_validation")
logger.setLevel(logging.INFO)


class SchemaValidation(SchemaValidationStrategy):
    """Strategy for validating metadata against JSON schema for v1.2.0."""
    
    def validate_schema(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata against v1.2.0 schema.
        
        Args:
            metadata (Dict): Package metadata to validate against schema
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether schema validation was successful
                - List[str]: List of schema validation errors
        """
        try:
            # Load schema for v1.2.0
            schema = get_package_schema(version="1.2.0", force_update=context.force_schema_update)
            if not schema:
                error_msg = "Failed to load package schema version 1.2.0"
                logger.error(error_msg)
                return False, [error_msg]
            
            # Validate against schema
            jsonschema.validate(instance=metadata, schema=schema)
            return True, []
            
        except jsonschema.exceptions.ValidationError as e:
            return False, [f"Schema validation error: {e.message}"]
        except Exception as e:
            return False, [f"Error during schema validation: {str(e)}"]