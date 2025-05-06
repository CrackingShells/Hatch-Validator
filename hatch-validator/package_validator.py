import json
import logging
import jsonschema
import importlib.util
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Callable
from packaging import version, specifiers

from schemas_retriever import get_package_schema

class PackageValidationError(Exception):
    """Exception raised for package validation errors."""
    pass

class HatchPackageValidator:
    def __init__(self, version: str = "latest", allow_local_dependencies: bool = True, force_schema_update: bool = False):
        """Initialize the Hatch package validator.
        
        Args:
            version: Version of the schema to use, or "latest"
            allow_local_dependencies: Whether to allow local dependencies
            force_schema_update: Whether to force a schema update check
        """
        self.logger = logging.getLogger("hatch.package_validator")
        self.logger.setLevel(logging.INFO)
        self.version = version
        self.allow_local_dependencies = allow_local_dependencies
        self.force_schema_update = force_schema_update
    
    def _run_validation(self, validator_func: Callable, *args, **kwargs) -> Tuple[bool, List[str]]: 
        """
        Common pattern for running validation functions that return (is_valid, errors)
        
        Args:
            validator_func: Validation function to run
            *args, **kwargs: Arguments to pass to the validator function
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list of validation errors)
        """
        try:
            return validator_func(*args, **kwargs)
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]
    
    def validate_metadata_schema(self, metadata: Dict) -> Tuple[bool, List[str]]: 
        """
        Validate the metadata against the JSON schema.
        
        Args:
            metadata: The metadata to validate
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list of validation errors)
        """
        # Load schema using the schema retriever
        schema = get_package_schema(version=self.version, force_update=self.force_schema_update)
        if not schema:
            error_msg = f"Failed to load package schema version {self.version}"
            self.logger.error(error_msg)
            return False, [error_msg]
        
        # Validate against schema
        try:
            jsonschema.validate(instance=metadata, schema=schema)
            return True, []
        except jsonschema.exceptions.ValidationError as e:
            return False, [f"Schema validation error: {e.message}"]
    
    def validate_entry_point_exists(self, package_dir: Path, entry_point: str) -> Tuple[bool, List[str]]: 
        """
        Validate that the entry point file exists.
        
        Args:
            package_dir: Path to the package directory
            entry_point: Name of the entry point file
            
        Returns:
            Tuple[bool, List[str]]: (exists, list of validation errors)
        """
        entry_path = package_dir / entry_point
        if not entry_path.exists():
            return False, [f"Entry point file '{entry_point}' does not exist"]
        if not entry_path.is_file():
            return False, [f"Entry point '{entry_point}' is not a file"]
        return True, []
    
    def validate_tools_exist(self, package_dir: Path, entry_point: str, tools: List[Dict]) -> Tuple[bool, List[str]]: 
        """
        Validate that the tools declared in metadata exist in the entry point file.
        
        Args:
            package_dir: Path to the package directory
            entry_point: Name of the entry point file
            tools: List of tool definitions from metadata
            
        Returns:
            Tuple[bool, List[str]]: (all_exist, list of validation errors)
        """
        if not tools:
            return True, []
            
        errors = []
        all_exist = True
        
        # Import the module
        try:
            module_path = package_dir / entry_point
            spec = importlib.util.spec_from_file_location("module.name", module_path)
            if spec is None or spec.loader is None:
                return False, [f"Could not load entry point module: {entry_point}"]
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Check for each tool
            for tool in tools:
                tool_name = tool.get('name')
                if not tool_name:
                    errors.append(f"Tool missing name in metadata")
                    all_exist = False
                    continue
                    
                if not hasattr(module, tool_name):
                    errors.append(f"Tool '{tool_name}' not found in entry point")
                    all_exist = False
                    continue
                    
                # Ensure it's a callable function
                tool_obj = getattr(module, tool_name)
                if not callable(tool_obj):
                    errors.append(f"Tool '{tool_name}' exists but is not a callable function")
                    all_exist = False
                    
        except Exception as e:
            return False, [f"Error validating tools: {str(e)}"]
            
        return all_exist, errors
    
    def validate_dependencies(self, metadata: Dict, available_packages: List[Dict] = None) -> Tuple[bool, List[str]]: 
        """
        Validate that all dependencies specified in metadata exist and are compatible.
        
        Args:
            metadata: Package metadata
            available_packages: List of available packages in the current environment
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list of validation errors)
        """
        errors = []
        is_valid = True
        
        hatch_dependencies = metadata.get('hatch_dependencies', [])
        
        # Check that no local dependencies exist if they're not allowed
        if not self.allow_local_dependencies:
            local_deps = [dep for dep in hatch_dependencies if dep.get('type') == 'local']
            if local_deps:
                for dep in local_deps:
                    errors.append(f"Local dependency '{dep.get('name')}' not allowed in this context")
                is_valid = False
        
        # Validate local URI paths and additional dependency constraints
        # that aren't covered by the base JSON Schema
        for dep in hatch_dependencies:
            dep_name = dep.get('name')
            dep_type = dep.get('type', 'remote')  # Default to remote if not specified
            
            # Check that local dependencies have a URI
            if dep_type == 'local':
                uri = dep.get('uri')
                if not uri:
                    errors.append(f"Local dependency '{dep_name}' is missing required field 'uri'")
                    is_valid = False
                    continue
                    
                # Check URI validity (file:// prefix) - specific to local dependencies
                if not uri.startswith('file://'):
                    errors.append(f"Local dependency URI must start with 'file://' for '{dep_name}'")
                    is_valid = False
            
            # Validate version constraint syntax
            version_constraint = dep.get('version_constraint')
            if version_constraint:
                try:
                    specifiers.SpecifierSet(version_constraint)
                except Exception as e:
                    errors.append(f"Invalid version constraint '{version_constraint}' for '{dep_name}': {str(e)}")
                    is_valid = False
        
        # Validate against available packages if provided
        if available_packages and is_valid:
            avail_valid, avail_errors = self._validate_against_available_packages(
                hatch_dependencies, available_packages
            )
            if not avail_valid:
                errors.extend(avail_errors)
                is_valid = False
        
        return is_valid, errors
    
    def _validate_against_available_packages(
        self, dependencies: List[Dict], available_packages: List[Dict]
    ) -> Tuple[bool, List[str]]: 
        """
        Validate dependencies against available packages.
        
        Args:
            dependencies: List of dependency definitions
            available_packages: List of available packages
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, errors)
        """
        errors = []
        is_valid = True
        available_pkg_dict = {pkg.get('name'): pkg for pkg in available_packages}
        
        for dep in dependencies:
            dep_name = dep.get('name')
            dep_type = dep.get('type', 'remote')  # Default to remote if not specified
            
            if dep_type == 'local':
                # For local dependencies, check URI path exists if specified
                uri = dep.get('uri')
                if uri and uri.startswith('file://'):
                    path = Path(uri[7:])
                    if not path.exists() or not path.is_dir():
                        errors.append(f"Local dependency path does not exist: {uri}")
                        is_valid = False
            else:
                # For remote dependencies, check if they're in available packages
                if dep_name not in available_pkg_dict:
                    errors.append(f"Remote dependency '{dep_name}' not found in available packages")
                    is_valid = False
                    continue
                    
                # Check version constraint if specified
                version_constraint = dep.get('version_constraint')
                if version_constraint:
                    try:
                        installed_version = available_pkg_dict[dep_name].get('version')
                        if installed_version:
                            spec = specifiers.SpecifierSet(version_constraint)
                            if not spec.contains(installed_version):
                                errors.append(
                                    f"Remote dependency '{dep_name}' version {installed_version} does not satisfy constraint {version_constraint}"
                                )
                                is_valid = False
                    except Exception as e:
                        errors.append(f"Error checking version constraint for '{dep_name}': {str(e)}")
                        is_valid = False
                    
        return is_valid, errors
        
    def validate_package(self, package_dir: Path, available_packages: List[Dict] = None) -> Tuple[bool, Dict[str, Any]]: 
        """
        Validate a Hatch package in the specified directory.
        
        Args:
            package_dir: Path to the package directory
            available_packages: List of available packages in the current environment
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, validation results)
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
        
        # Validate metadata schema
        schema_valid, schema_errors = self._run_validation(
            self.validate_metadata_schema, metadata
        )
        results['metadata_schema']['valid'] = schema_valid
        results['metadata_schema']['errors'] = schema_errors
        
        # If schema validation failed, don't continue
        if not schema_valid:
            results['valid'] = False
            return False, results
        
        # Validate dependencies
        deps_valid, deps_errors = self._run_validation(
            self.validate_dependencies, metadata, available_packages
        )
        results['dependencies']['valid'] = deps_valid
        results['dependencies']['errors'] = deps_errors
        
        if not deps_valid:
            results['valid'] = False
        
        # Get entry point from metadata
        entry_point = metadata.get('entry_point')
        if not entry_point:
            results['valid'] = False
            results['entry_point']['errors'].append("No entry_point specified in metadata")
            return False, results
        
        # Validate entry point
        entry_valid, entry_errors = self._run_validation(
            self.validate_entry_point_exists, package_dir, entry_point
        )
        results['entry_point']['valid'] = entry_valid
        results['entry_point']['errors'] = entry_errors
        
        if not entry_valid:
            results['valid'] = False
        
        # Validate tools
        tools = metadata.get('tools', [])
        if tools:
            tools_valid, tools_errors = self._run_validation(
                self.validate_tools_exist, package_dir, entry_point, tools
            )
            results['tools']['valid'] = tools_valid
            results['tools']['errors'] = tools_errors
            
            if not tools_valid:
                results['valid'] = False
        else:
            results['tools']['valid'] = True
        
        return results['valid'], results