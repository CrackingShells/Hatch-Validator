import logging
from typing import Dict, List, Tuple

from hatch_validator.core.validation_strategy import EntryPointValidationStrategy
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.package.package_service import PackageService

logger = logging.getLogger("hatch_validator.schemas.v1_1_0.entry_point_validation")
logger.setLevel(logging.INFO)

class EntryPointValidation(EntryPointValidationStrategy):
    """Strategy for validating entry point files for v1.1.0."""
    
    def validate_entry_point(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate entry point according to v1.1.0 schema.
        
        Args:
            metadata (Dict): Package metadata containing entry point information
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether entry point validation was successful
                - List[str]: List of entry point validation errors
        """
        # Use PackageService from context
        package_service = context.get_data("package_service", None)
        if package_service is None:
            package_service = PackageService(metadata)
        entry_point = package_service.get_entry_point()
        if not entry_point:
            logger.error("No entry_point specified in metadata")
            return False, ["No entry_point specified in metadata"]
        
        if not context.package_dir:
            logger.error("Package directory not provided for entry point validation")
            return False, ["Package directory not provided for entry point validation"]
        
        entry_path = context.package_dir / entry_point
        if not entry_path.exists():
            logger.error(f"Entry point file '{entry_point}' does not exist")
            return False, [f"Entry point file '{entry_point}' does not exist"]
        
        if not entry_path.is_file():
            logger.error(f"Entry point '{entry_point}' is not a file")
            return False, [f"Entry point '{entry_point}' is not a file"]
        
        return True, []