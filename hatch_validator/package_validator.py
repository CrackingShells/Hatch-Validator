"""Package validation module using Chain of Responsibility and Strategy patterns.

This module provides the main HatchPackageValidator class that uses the new
extensible validation architecture for validating Hatch packages against
different schema versions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

from .schema_validators import ValidatorFactory, ValidationContext
from .schemas_retriever import get_registry_schema


class PackageValidationError(Exception):
    """Exception raised for package validation errors."""
    pass


class HatchPackageValidator:
    """Hatch package validator using Chain of Responsibility pattern.
    
    This validator uses the new extensible validation architecture that can
    handle multiple schema versions through a chain of specialized validators.
    """
    
    def __init__(self, version: str = "latest", allow_local_dependencies: bool = True, 
                 force_schema_update: bool = False, registry_data: Optional[Dict] = None):
        """Initialize the Hatch package validator.
        
        Args:
            version (str, optional): Version of the schema to use, or "latest". Defaults to "latest".
            allow_local_dependencies (bool, optional): Whether to allow local dependencies. Defaults to True.
            force_schema_update (bool, optional): Whether to force a schema update check. Defaults to False.
            registry_data (Dict, optional): Registry data to use for dependency validation. Defaults to None.
        """
        self.logger = logging.getLogger("hatch.package_validator")
        self.logger.setLevel(logging.INFO)
        self.version = version
        self.allow_local_dependencies = allow_local_dependencies
        self.force_schema_update = force_schema_update
        self.registry_data = registry_data
    
    def validate_pkg_metadata(self, metadata: Dict) -> Tuple[bool, List[str]]:
        """Validate the package's metadata against the package JSON schema.
        
        Uses the new Chain of Responsibility validator system to validate
        metadata against the appropriate schema version.
        
        Args:
            metadata (Dict): The metadata to validate
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether validation was successful
                - List[str]: List of validation errors
        """
        try:
            # Determine the target schema version
            schema_version = self._determine_schema_version(metadata)
            
            # Create validator chain for the target version
            validator = ValidatorFactory.create_validator_chain(schema_version)
            
            # Create validation context (metadata-only validation)
            context = ValidationContext(
                registry_data=self.registry_data,
                allow_local_dependencies=self.allow_local_dependencies,
                force_schema_update=self.force_schema_update
            )
            
            # Run validation through the chain
            return validator.validate(metadata, context)
            
        except ValueError as e:
            if "Unsupported schema version" in str(e):
                return False, [f"Unsupported schema version: {metadata.get('package_schema_version', 'unknown')}"]
            raise
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]
    
    def validate_registry_metadata(self, metadata: Dict) -> Tuple[bool, List[str]]:
        """Validate the registry's metadata against the registry JSON schema.
        
        Args:
            metadata (Dict): The metadata to validate
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether validation was successful
                - List[str]: List of validation errors
        """
        # Load schema using the schema retriever
        schema = get_registry_schema(version=self.version, force_update=self.force_schema_update)
        if not schema:
            error_msg = f"Failed to load registry schema version {self.version}"
            self.logger.error(error_msg)
            return False, [error_msg]
        
        # Validate against schema
        try:
            import jsonschema
            jsonschema.validate(instance=metadata, schema=schema)
            return True, []
        except jsonschema.exceptions.ValidationError as e:
            return False, [f"Registry validation error: {e.message}"]
        except Exception as e:
            return False, [f"Error during registry validation: {str(e)}"]
    
    def validate_package(self, package_dir: Path, pending_update: Optional[Tuple[str, Dict]] = None) -> Tuple[bool, Dict[str, Any]]:
        """Validate a Hatch package in the specified directory.
        
        Uses the new Chain of Responsibility validator system for comprehensive
        package validation including metadata, dependencies, entry points, and tools.
        
        Args:
            package_dir (Path): Path to the package directory
            pending_update (Tuple[str, Dict], optional): Optional tuple (pkg_name, metadata) with pending update information. Defaults to None.
            
        Returns:
            Tuple[bool, Dict[str, Any]]: Tuple containing:
                - bool: Whether validation was successful
                - Dict[str, Any]: Detailed validation results
        """
        results = {
            'valid': True,
            'metadata_schema': {'valid': False, 'errors': []},
            'entry_point': {'valid': False, 'errors': []},
            'tools': {'valid': False, 'errors': []},
            'dependencies': {'valid': True, 'errors': []},
            'metadata': None
        }
        
        # Check if package directory exists
        if not package_dir.exists() or not package_dir.is_dir():
            results['valid'] = False
            results['metadata_schema']['errors'].append(f"Package directory does not exist: {package_dir}")
            return False, results
        
        # Check for metadata file
        metadata_path = package_dir / "hatch_metadata.json"
        if not metadata_path.exists():
            results['valid'] = False
            results['metadata_schema']['errors'].append("hatch_metadata.json not found")
            return False, results
        
        # Load metadata
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
                results['metadata'] = metadata
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            results['valid'] = False
            results['metadata_schema']['errors'].append(f"Failed to parse metadata: {e}")
            return False, results
        
        # Use new validation system for comprehensive validation
        try:
            # Determine the target schema version
            schema_version = self._determine_schema_version(metadata)
            
            # Create validator chain for the target version
            validator = ValidatorFactory.create_validator_chain(schema_version)
            
            # Create validation context with package directory
            context = ValidationContext(
                package_dir=package_dir,
                registry_data=self.registry_data,
                allow_local_dependencies=self.allow_local_dependencies,
                force_schema_update=self.force_schema_update
            )
            
            # Add pending update information for circular dependency detection
            if pending_update:
                context.set_data("pending_update", pending_update)
            
            # Run comprehensive validation through the chain
            is_valid, errors = validator.validate(metadata, context)
            
            if is_valid:
                # All validations passed
                results['metadata_schema']['valid'] = True
                results['entry_point']['valid'] = True
                results['tools']['valid'] = True
                results['dependencies']['valid'] = True
            else:
                # Parse errors to categorize them for backward compatibility
                results['valid'] = False
                self._categorize_validation_errors(errors, results)
                        
        except ValueError as e:
            if "Unsupported schema version" in str(e):
                results['valid'] = False
                results['metadata_schema']['errors'].append(f"Unsupported schema version: {schema_version}")
            else:
                results['valid'] = False
                results['metadata_schema']['errors'].append(f"Validation error: {str(e)}")
        except Exception as e:
            results['valid'] = False
            results['metadata_schema']['errors'].append(f"Validation system error: {str(e)}")
            
        return results['valid'], results
    
    def _determine_schema_version(self, metadata: Dict) -> str:
        """Determine the schema version to use for validation.
        
        Args:
            metadata (Dict): Package metadata
            
        Returns:
            str: Schema version to use
        """
        # First, check if metadata specifies a schema version
        schema_version = metadata.get("package_schema_version")
        if schema_version:
            return schema_version
        
        # Fallback to validator's configured version
        if self.version == "latest":
            return "1.1.0"  # Current latest version
        else:
            return self.version
    
    def _categorize_validation_errors(self, errors: List[str], results: Dict[str, Any]) -> None:
        """Categorize validation errors into appropriate result categories.
        
        This method maintains backward compatibility with the original result structure
        by parsing error messages and categorizing them appropriately.
        
        Args:
            errors (List[str]): List of validation errors
            results (Dict[str, Any]): Results dictionary to update
        """
        # Reset all validation statuses since we'll set them based on errors
        results['metadata_schema']['valid'] = True
        results['entry_point']['valid'] = True
        results['tools']['valid'] = True
        results['dependencies']['valid'] = True
        
        # Categorize each error
        for error in errors:
            error_lower = error.lower()
            
            # Logging to debug error categorization
            self.logger.debug(f"Categorizing error: {error}")
            
            if "schema validation" in error_lower or "failed to load" in error_lower:
                results['metadata_schema']['errors'].append(error)
                results['metadata_schema']['valid'] = False
            elif "entry point" in error_lower:
                results['entry_point']['errors'].append(error)
                results['entry_point']['valid'] = False
            elif "tool" in error_lower or "function" in error_lower:
                results['tools']['errors'].append(error)
                results['tools']['valid'] = False
            elif any(keyword in error_lower for keyword in ['dependency', 'circular', 'constraint', 'not found', 'version']):
                results['dependencies']['errors'].append(error)
                results['dependencies']['valid'] = False
            else:
                # Default: assign to metadata schema
                results['metadata_schema']['errors'].append(error)
                results['metadata_schema']['valid'] = False