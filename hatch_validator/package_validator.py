import ast
import json
import logging
import jsonschema
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional, Callable

from .schemas_retriever import get_package_schema
from .dependency_resolver import DependencyResolver

class PackageValidationError(Exception):
    """Exception raised for package validation errors."""
    pass

class HatchPackageValidator:
    def __init__(self, version: str = "latest", allow_local_dependencies: bool = True, 
                 force_schema_update: bool = False, registry_data: Optional[Dict] = None):
        """Initialize the Hatch package validator.
        
        Args:
            version: Version of the schema to use, or "latest"
            allow_local_dependencies: Whether to allow local dependencies
            force_schema_update: Whether to force a schema update check
            registry_data: Registry data to use for dependency validation
        """
        self.logger = logging.getLogger("hatch.package_validator")
        self.logger.setLevel(logging.INFO)
        self.version = version
        self.allow_local_dependencies = allow_local_dependencies
        self.force_schema_update = force_schema_update
        self.dependency_resolver = DependencyResolver(registry_data)
    
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
            with open(module_path, 'r', encoding='utf-8') as file:
                try:
                    tree = ast.parse(file.read(), filename=str(module_path))
                    
                    # Get all function names defined in the file
                    function_names = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
                    
                    self.logger.debug(f"Found functions in {entry_point}: {function_names}")
                    
                    # Check for each tool
                    for tool in tools:
                        tool_name = tool.get('name')
                        if not tool_name:
                            self.logger.error(f"Tool metadata missing name: {tool}")
                            errors.append(f"Tool missing name in metadata")
                            all_exist = False
                            continue
                        
                        # Check if the tool function is defined in the file
                        if tool_name not in function_names:
                            self.logger.error(f"Tool '{tool_name}' not found in entry point")
                            errors.append(f"Tool '{tool_name}' not found in entry point")
                            all_exist = False
                    
                except SyntaxError as e:
                    self.logger.error(f"Syntax error in {entry_point}: {e}")
                    return False, [f"Syntax error in {entry_point}: {e}"]
                    
        except Exception as e:
            self.logger.error(f"Error validating tools: {str(e)}")
            return False, [f"Error validating tools: {str(e)}"]
            
        return all_exist, errors
    
    def validate_dependencies(self, metadata: Dict, package_dir: Optional[Path] = None,
                         pending_update: Optional[Tuple[str, Dict]] = None) -> Tuple[bool, List[str]]: 
        """
        Validate that all dependencies specified in metadata exist and are compatible.
        Uses registry data as source of truth for remote dependencies.
        
        Args:
            metadata: Package metadata
            package_dir: Optional path to package directory for resolving local dependencies
            pending_update: Optional tuple (pkg_name, metadata) with pending update information
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list of validation errors)
        """
        errors = []
        is_valid = True
        
        hatch_dependencies = metadata.get('hatch_dependencies', [])

        self.logger.debug(f"{metadata.get('name')} dependencies validation for: {hatch_dependencies}")
        
        # Early check for local dependencies if they're not allowed
        if not self.allow_local_dependencies:
            local_deps = [dep for dep in hatch_dependencies if dep.get('type') == 'local']
            if local_deps:
                for dep in local_deps:
                    self.logger.error(f"Local dependency '{dep.get('name')}' not allowed in this context")
                    errors.append(f"Local dependency '{dep.get('name')}' not allowed in this context")
                is_valid = False
                return is_valid, errors
        
        # Use the dependency resolver for validation
        validation_valid, validation_errors = self.dependency_resolver.validate_dependencies(
            hatch_dependencies,
            package_dir
        )
        
        if not validation_valid:
            errors.extend(validation_errors)
            is_valid = False
            
        # Check for circular dependencies
        try:
            has_cycles, cycles = self.dependency_resolver.detect_dependency_cycles(
                hatch_dependencies,
                package_dir,
                pending_update
            )
            if has_cycles:
                for cycle in cycles:
                    cycle_str = " -> ".join(cycle)
                    self.logger.error(f"Circular dependency detected: {cycle_str}")
                    errors.append(f"Circular dependency detected: {cycle_str}")
                is_valid = False
        except Exception as e:
            self.logger.warning(f"Could not check for circular dependencies: {e}")
        
        return is_valid, errors
        
    def validate_package(self, package_dir: Path, pending_update: Optional[Tuple[str, Dict]] = None) -> Tuple[bool, Dict[str, Any]]: 
        """
        Validate a Hatch package in the specified directory.
        Uses registry data for remote dependencies validation.
        
        Args:
            package_dir: Path to the package directory
            pending_update: Optional tuple (pkg_name, metadata) with pending update information
            
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
        
        # Validate dependencies using registry data
        deps_valid, deps_errors = self._run_validation(
            self.validate_dependencies, metadata, package_dir, pending_update
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