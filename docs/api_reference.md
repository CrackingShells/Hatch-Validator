# API Reference

## Core Components

### ValidationContext

The `ValidationContext` class provides shared resources and state during validation.

```python
class ValidationContext:
    """Context object containing resources and configuration for validation.
    
    This class carries shared state throughout the validation process, including
    package directory, registry data, and validation settings.
    """
    
    def __init__(self, package_dir: Path, registry_data: Optional[Dict] = None, 
                 allow_local_dependencies: bool = True, force_schema_update: bool = False):
        """Initialize validation context.
        
        Args:
            package_dir (Path): Directory containing the package to validate
            registry_data (Dict, optional): Registry data for dependency resolution
            allow_local_dependencies (bool, optional): Whether to allow local dependencies. Defaults to True.
            force_schema_update (bool, optional): Whether to force schema cache update. Defaults to False.
        """
```

#### Methods

- `get_data(key: str) -> Any`: Get context-specific data
- `set_data(key: str, value: Any) -> None`: Set context-specific data

### ValidatorFactory

Factory class for creating validator chains.

```python
class ValidatorFactory:
    """Factory class for creating schema validator chains."""
    
    @staticmethod
    def create_validator_chain(target_version: Optional[str] = None) -> SchemaValidator:
        """Create appropriate validator chain based on target version.
        
        Args:
            target_version (str, optional): Specific schema version to target
            
        Returns:
            SchemaValidator: Head of the validator chain
            
        Raises:
            ValueError: If the target version is not supported
        """
```

### SchemaValidator (Base)

Abstract base class for all schema validators.

```python
class SchemaValidator(ABC):
    """Abstract base class for schema validators implementing Chain of Responsibility pattern."""
    
    def __init__(self, next_validator: Optional['SchemaValidator'] = None):
        """Initialize validator with optional next validator in chain."""
    
    @abstractmethod
    def can_handle(self, schema_version: str) -> bool:
        """Determine if this validator can handle the given schema version."""
    
    @abstractmethod
    def validate(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata against schema."""
```

## Strategy Interfaces

### DependencyValidationStrategy

Abstract strategy for dependency validation.

```python
class DependencyValidationStrategy(ValidationStrategy):
    """Abstract strategy for validating package dependencies."""
    
    @abstractmethod
    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate dependencies in package metadata.
        
        Args:
            metadata (Dict): Package metadata containing dependency information
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether dependency validation was successful
                - List[str]: List of dependency validation errors
        """
```

### SchemaValidationStrategy

Abstract strategy for JSON schema validation.

```python
class SchemaValidationStrategy(ValidationStrategy):
    """Abstract strategy for validating metadata against JSON schema."""
    
    @abstractmethod
    def validate_schema(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata against JSON schema.
        
        Args:
            metadata (Dict): Package metadata to validate
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether schema validation was successful
                - List[str]: List of schema validation errors
        """
```

### EntryPointValidationStrategy

Abstract strategy for entry point validation.

```python
class EntryPointValidationStrategy(ValidationStrategy):
    """Abstract strategy for validating package entry points."""
    
    @abstractmethod
    def validate_entry_point(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate entry point in package metadata.
        
        Args:
            metadata (Dict): Package metadata containing entry point information
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether entry point validation was successful
                - List[str]: List of entry point validation errors
        """
```

### ToolsValidationStrategy

Abstract strategy for tools validation.

```python
class ToolsValidationStrategy(ValidationStrategy):
    """Abstract strategy for validating package tools."""
    
    @abstractmethod
    def validate_tools(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate tools in package metadata.
        
        Args:
            metadata (Dict): Package metadata containing tools information
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether tools validation was successful
                - List[str]: List of tools validation errors
        """
```

## Utility Modules

### DependencyGraph

Utility class for graph operations on dependency structures.

```python
class DependencyGraph:
    """Utility class for graph operations on dependency structures."""
    
    def create_adjacency_list(self, dependencies: List[Dict]) -> Dict[str, List[str]]:
        """Create adjacency list representation from dependencies.
        
        Args:
            dependencies (List[Dict]): List of dependency dictionaries
            
        Returns:
            Dict[str, List[str]]: Adjacency list mapping packages to their dependencies
        """
    
    def has_cycles(self, adjacency_list: Dict[str, List[str]]) -> bool:
        """Check if graph has cycles using DFS.
        
        Args:
            adjacency_list (Dict[str, List[str]]): Graph as adjacency list
            
        Returns:
            bool: True if graph contains cycles, False otherwise
        """
    
    def find_cycles(self, adjacency_list: Dict[str, List[str]]) -> List[List[str]]:
        """Find all cycles in the graph.
        
        Args:
            adjacency_list (Dict[str, List[str]]): Graph as adjacency list
            
        Returns:
            List[List[str]]: List of cycles, each cycle is a list of package names
        """
    
    def topological_sort(self, adjacency_list: Dict[str, List[str]]) -> Optional[List[str]]:
        """Perform topological sort on the graph.
        
        Args:
            adjacency_list (Dict[str, List[str]]): Graph as adjacency list
            
        Returns:
            Optional[List[str]]: Topologically sorted list of packages, None if graph has cycles
        """
```

### VersionConstraintValidator

Utility class for version constraint validation and parsing.

```python
class VersionConstraintValidator:
    """Utility class for validating and parsing version constraints."""
    
    def is_valid_constraint(self, constraint: str) -> bool:
        """Check if a version constraint string is valid.
        
        Args:
            constraint (str): Version constraint to validate
            
        Returns:
            bool: True if constraint is valid, False otherwise
        """
    
    def parse_constraint(self, constraint: str) -> Optional[packaging.specifiers.SpecifierSet]:
        """Parse version constraint string into SpecifierSet.
        
        Args:
            constraint (str): Version constraint to parse
            
        Returns:
            Optional[SpecifierSet]: Parsed constraint, None if invalid
        """
    
    def is_compatible(self, version: str, constraint: str) -> bool:
        """Check if a version satisfies a constraint.
        
        Args:
            version (str): Version to check
            constraint (str): Version constraint to check against
            
        Returns:
            bool: True if version satisfies constraint, False otherwise
        """
    
    def normalize_constraint(self, constraint: str) -> str:
        """Normalize version constraint format.
        
        Args:
            constraint (str): Version constraint to normalize
            
        Returns:
            str: Normalized constraint string
        """
```

### RegistryClient

Utility class for registry data access and caching.

```python
class RegistryClient:
    """Utility class for registry data access and caching."""
    
    def __init__(self, registry_data: Optional[Dict] = None, cache_ttl: int = 3600):
        """Initialize registry client.
        
        Args:
            registry_data (Dict, optional): Pre-loaded registry data
            cache_ttl (int, optional): Cache time-to-live in seconds. Defaults to 3600.
        """
    
    def package_exists(self, package_name: str) -> bool:
        """Check if package exists in registry.
        
        Args:
            package_name (str): Name of package to check
            
        Returns:
            bool: True if package exists, False otherwise
        """
    
    def get_package_versions(self, package_name: str) -> List[str]:
        """Get available versions for a package.
        
        Args:
            package_name (str): Name of package
            
        Returns:
            List[str]: List of available version strings
        """
    
    def get_package_metadata(self, package_name: str, version: str) -> Optional[Dict]:
        """Get metadata for specific package version.
        
        Args:
            package_name (str): Name of package
            version (str): Version of package
            
        Returns:
            Optional[Dict]: Package metadata, None if not found
        """
    
    def load_from_file(self, file_path: Path) -> None:
        """Load registry data from file.
        
        Args:
            file_path (Path): Path to registry file
        """
```

## Schema-Specific Implementations

### v1.1.0 Dependency Validation

Implementation of dependency validation for schema version 1.1.0.

```python
class DependencyValidationV1_1_0(DependencyValidationStrategy):
    """Dependency validation strategy for v1.1.0 schema."""
    
    def __init__(self):
        """Initialize the v1.1.0 dependency validation strategy."""
    
    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate dependencies according to v1.1.0 schema.
        
        In v1.1.0, dependencies are stored in separate arrays:
        - hatch_dependencies: Array of Hatch package dependencies
        - python_dependencies: Array of Python package dependencies
        
        Args:
            metadata (Dict): Package metadata containing dependency information
            context (ValidationContext): Validation context with resources
            
        Returns:
            Tuple[bool, List[str]]: Tuple containing:
                - bool: Whether dependency validation was successful
                - List[str]: List of dependency validation errors
        """
```

### v1.1.0 Schema Validator

Complete validator implementation for schema version 1.1.0.

```python
class SchemaValidator(SchemaValidator):
    """Validator for schema version 1.1.0."""
    
    def __init__(self, next_validator=None):
        """Initialize the v1.1.0 validator with strategies."""
    
    def can_handle(self, schema_version: str) -> bool:
        """Determine if this validator can handle v1.1.0 schema."""
    
    def validate(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata against v1.1.0 schema."""
```

## Error Handling

### Exception Classes

```python
class PackageValidationError(Exception):
    """Exception raised when package validation fails."""
    
    def __init__(self, message: str, errors: List[str]):
        """Initialize validation error.
        
        Args:
            message (str): Error message
            errors (List[str]): List of specific validation errors
        """
        super().__init__(message)
        self.errors = errors

class DependencyResolutionError(Exception):
    """Exception raised when dependency resolution fails."""
    pass
```

## Usage Examples

### Basic Package Validation

```python
from hatch_validator import HatchPackageValidator
from pathlib import Path

# Create validator
validator = HatchPackageValidator()

# Validate package
package_dir = Path("path/to/package")
is_valid, errors = validator.validate_package(package_dir)

if not is_valid:
    print("Validation failed:")
    for error in errors:
        print(f"  - {error}")
```

### Custom Validation Context

```python
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.core.validator_factory import ValidatorFactory

# Create custom context
context = ValidationContext(
    package_dir=Path("path/to/package"),
    registry_data=custom_registry_data,
    allow_local_dependencies=False
)

# Create validator for specific version
validator = ValidatorFactory.create_validator_chain(target_version="1.1.0")

# Validate with custom context
is_valid, errors = validator.validate(metadata, context)
```

### Using Utility Modules Directly

```python
from hatch_validator.utils.dependency_graph import DependencyGraph
from hatch_validator.utils.version_utils import VersionConstraintValidator

# Check for circular dependencies
graph = DependencyGraph()
adjacency_list = graph.create_adjacency_list(dependencies)
has_cycles = graph.has_cycles(adjacency_list)

# Validate version constraints
version_validator = VersionConstraintValidator()
is_valid = version_validator.is_valid_constraint(">=1.0.0,<2.0.0")
```
