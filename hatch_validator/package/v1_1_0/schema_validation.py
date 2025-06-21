import logging
import jsonschema
from typing import Dict, List, Tuple

from hatch_validator.schemas.schemas_retriever import get_package_schema
from hatch_validator.core.validation_strategy import SchemaValidationStrategy
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.package.package_service import PackageService

logger = logging.getLogger("hatch_validator.schemas.v1_1_0.schema_validation")
logger.setLevel(logging.INFO)

class SchemaValidation(SchemaValidationStrategy):
    """Strategy for validating metadata against JSON schema for v1.1.0."""
    
    def validate_schema(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata against v1.1.0 schema.
        
        Args:
            metadata (Dict): Package metadata to validate against schema
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether schema validation was successful
                - List[str]: List of schema validation errors
        """
        try:
            package_service = context.get_data("package_service", None)
            if package_service is None:
                package_service = PackageService(metadata)
            schema_version = package_service.get_field("package_schema_version")
            schema = get_package_schema(version=schema_version, force_update=context.force_schema_update)
            if not schema:
                error_msg = f"Failed to load package schema version {schema_version}"
                logger.error(error_msg)
                return False, [error_msg]
            
            jsonschema.validate(instance=metadata, schema=schema)
            return True, []
            
        except jsonschema.exceptions.ValidationError as e:
            return False, [f"Schema validation error: {e.message}"]
        except Exception as e:
            return False, [f"Error during schema validation: {str(e)}"]