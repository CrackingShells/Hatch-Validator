# PackageService Guide

This article is about:
- Version-agnostic package metadata access through PackageService
- How PackageService abstracts schema versioning using accessor chains
- API overview and key methods for metadata operations
- Integration patterns with the Chain of Responsibility architecture

## Overview

The PackageService class provides a unified interface for accessing package metadata regardless of schema version. It automatically detects the schema version from metadata and creates the appropriate accessor chain to handle version-specific data structures.

## Core Concepts

### Automatic Schema Detection

PackageService automatically detects the package schema version and creates the appropriate accessor chain:

```python
from hatch_validator.package.package_service import PackageService

# Service automatically detects schema version from metadata
service = PackageService(metadata)

# No need to specify schema version - it's handled automatically
dependencies = service.get_dependencies()
```

### Accessor Chain Integration

The service uses the HatchPkgAccessorFactory to create accessor chains that implement the Chain of Responsibility pattern:

1. **Schema Version Detection**: Extracts `package_schema_version` from metadata
2. **Chain Creation**: Creates accessor chain starting from detected version
3. **Delegation**: Each accessor handles its version or delegates to older versions
4. **Unified Interface**: Returns data through consistent method signatures

## API Reference

### Constructor

```python
PackageService(metadata: Optional[Dict[str, Any]] = None)
```

**Parameters:**
- `metadata`: Optional package metadata dictionary. If provided, automatically initializes the accessor chain.

### Core Methods

#### load_metadata()

```python
def load_metadata(self, metadata: Dict[str, Any]) -> None
```

Loads package metadata and initializes the appropriate accessor chain based on the detected schema version.

**Parameters:**
- `metadata`: Package metadata dictionary containing `package_schema_version`

**Raises:**
- `ValueError`: If `package_schema_version` is missing or no accessor can handle the version

#### get_dependencies()

```python
def get_dependencies(self) -> Dict[str, Any]
```

Returns all dependencies from the package metadata using version-appropriate access patterns.

**Returns:**
- Dictionary of dependencies organized by type (e.g., 'hatch', 'python', 'system', 'docker')

**Schema Version Handling:**
- **v1.1.0**: Returns `{'hatch': [...], 'python': [...]}`
- **v1.2.0+**: Returns unified dependency structure with all supported types

#### get_field()

```python
def get_field(self, field: str) -> Any
```

Retrieves a top-level field from package metadata using the appropriate accessor.

**Parameters:**
- `field`: Field name to retrieve (e.g., 'name', 'version', 'description')

**Returns:**
- Field value or None if not found

#### is_local_dependency()

```python
def is_local_dependency(self, dep: Dict[str, Any], root_dir: Optional[Path] = None) -> bool
```

Determines if a dependency is local using version-appropriate logic.

**Parameters:**
- `dep`: Dependency dictionary
- `root_dir`: Optional root directory for relative path resolution

**Returns:**
- True if dependency is local, False otherwise

### Utility Methods

#### is_loaded()

```python
def is_loaded(self) -> bool
```

Checks if package metadata is loaded and accessible.

**Returns:**
- True if metadata and accessor are available

## Schema Version Abstraction

### Version-Specific Behavior

The PackageService abstracts differences between schema versions:

**v1.1.0 Schema:**
- Separate `hatch_dependencies` and `python_dependencies` fields
- Basic dependency structure

**v1.2.0 Schema:**
- Unified `dependencies` structure
- Support for hatch, python, system, and docker dependency types
- Enhanced dependency metadata

**v1.2.1 Schema:**
- Dual entry point configuration
- Enhanced tools validation
- Backward compatibility with v1.2.0 dependency structure

### Consistent Interface

Regardless of schema version, the same method calls work:

```python
# This code works with any supported schema version
service = PackageService(metadata)
deps = service.get_dependencies()
name = service.get_field('name')
```

## Integration with Chain of Responsibility

### Accessor Chain Creation

When PackageService loads metadata, it:

1. **Extracts Schema Version**: Gets `package_schema_version` from metadata
2. **Creates Chain**: Uses HatchPkgAccessorFactory to create accessor chain
3. **Links Components**: Accessors are linked newest to oldest (e.g., v1.2.1 → v1.2.0 → v1.1.0)
4. **Delegates Requests**: Each accessor handles its concerns or delegates to the next

### Delegation Flow

For a v1.2.1 package requesting dependencies:

1. **v1.2.1 Accessor**: Handles dual entry point metadata, delegates dependency access to v1.2.0
2. **v1.2.0 Accessor**: Handles unified dependency structure, returns result
3. **Service**: Returns unified dependency data to caller

## Error Handling

### Common Exceptions

**ValueError**: Raised when:
- `package_schema_version` is missing from metadata
- No accessor can handle the detected schema version
- Metadata is not loaded when accessing data

**AttributeError**: Raised when:
- Requested field is not supported by the accessor chain

### Best Practices

```python
try:
    service = PackageService()
    service.load_metadata(metadata)
    dependencies = service.get_dependencies()
except ValueError as e:
    # Handle schema version or loading errors
    print(f"Metadata loading failed: {e}")
except AttributeError as e:
    # Handle unsupported field access
    print(f"Field access failed: {e}")
```

## Real-World Usage Examples

For comprehensive examples of PackageService usage in production environments, including integration with dependency orchestrators and environment managers, see [Programmatic Usage](../integration/ProgrammaticUsage.md).

## Related Documentation

- [RegistryService Guide](RegistryService.md) - Version-agnostic registry data access
- [Version-Agnostic Access Concepts](VersionAgnosticAccess.md) - Core principles and benefits
- [Chain of Responsibility Pattern](../../devs/architecture/ChainOfResponsibilityPattern.md) - Architectural foundation
- [Programmatic Usage](../integration/ProgrammaticUsage.md) - Real-world integration examples
