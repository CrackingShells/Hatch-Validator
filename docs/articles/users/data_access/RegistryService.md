# RegistryService Guide

This article is about:
- Version-agnostic registry data access through RegistryService
- Package discovery and version resolution capabilities
- API overview and key methods for registry operations
- Integration patterns with registry accessor chains

## Overview

The RegistryService class provides a unified interface for working with package registries regardless of registry schema version. It automatically detects the registry data format and creates the appropriate accessor chain to handle version-specific registry structures.

## Core Concepts

### Automatic Registry Schema Detection

RegistryService automatically detects the registry schema version and creates the appropriate accessor chain:

```python
from hatch_validator.registry.registry_service import RegistryService

# Service automatically detects registry schema from data
service = RegistryService(registry_data)

# No need to specify schema version - it's handled automatically
exists = service.package_exists("my-package")
```

### Registry Accessor Chain Integration

The service uses the RegistryAccessorFactory to create accessor chains that implement the Chain of Responsibility pattern:

1. **Schema Detection**: Analyzes registry data structure and format
2. **Chain Creation**: Creates accessor chain for detected registry version
3. **Delegation**: Each accessor handles its format or delegates to compatible versions
4. **Unified Interface**: Returns data through consistent method signatures

## API Reference

### Constructor

```python
RegistryService(registry_data: Optional[Dict[str, Any]] = None)
```

**Parameters:**
- `registry_data`: Optional registry data dictionary. If provided, automatically initializes the accessor chain.

### Core Methods

#### load_registry_data()

```python
def load_registry_data(self, registry_data: Dict[str, Any]) -> None
```

Loads registry data and initializes the appropriate accessor chain based on the detected registry format.

**Parameters:**
- `registry_data`: Registry data dictionary

**Raises:**
- `RegistryError`: If no accessor can handle the registry data format

#### Package Discovery Methods

##### package_exists()

```python
def package_exists(self, package_name: str, repo_name: Optional[str] = None) -> bool
```

Checks if a package exists in the registry.

**Parameters:**
- `package_name`: Name of the package to check
- `repo_name`: Optional repository name. If None, infers from package_name if present

**Returns:**
- True if package exists in the registry

##### get_all_package_names()

```python
def get_all_package_names(self, repo_name: Optional[str] = None) -> List[str]
```

Retrieves all package names from the registry.

**Parameters:**
- `repo_name`: Optional repository name. If None, returns packages from all repositories

**Returns:**
- List of all package names

#### Version Resolution Methods

##### find_compatible_version()

```python
def find_compatible_version(self, package_name: str, version_constraint: str) -> str
```

Finds a package version that satisfies the given version constraint.

**Parameters:**
- `package_name`: Name of the package
- `version_constraint`: Version constraint string (e.g., ">=1.0.0", "~=2.1.0")

**Returns:**
- Compatible version string

**Raises:**
- `VersionConstraintError`: If no compatible version is found

##### get_package_uri()

```python
def get_package_uri(self, package_name: str, version: str) -> str
```

Retrieves the download URI for a specific package version.

**Parameters:**
- `package_name`: Name of the package
- `version`: Specific version string

**Returns:**
- Package download URI

#### Repository Management Methods

##### list_repositories()

```python
def list_repositories(self) -> List[str]
```

Lists all repository names in the loaded registry.

**Returns:**
- List of repository names

##### repository_exists()

```python
def repository_exists(self, repo_name: str) -> bool
```

Checks if a repository exists in the loaded registry.

**Parameters:**
- `repo_name`: Repository name to check

**Returns:**
- True if repository exists

##### list_packages()

```python
def list_packages(self, repo_name: str) -> List[str]
```

Lists all package names in a specific repository.

**Parameters:**
- `repo_name`: Repository name

**Returns:**
- List of package names in the repository

### Utility Methods

#### is_loaded()

```python
def is_loaded(self) -> bool
```

Checks if registry data is loaded and accessible.

**Returns:**
- True if registry data and accessor are available

#### has_repository_name()

```python
def has_repository_name(self, package_name: str) -> bool
```

Checks if a package name includes a repository prefix (e.g., "repo:package").

**Parameters:**
- `package_name`: Package name to check

**Returns:**
- True if package name includes repository prefix

## Registry Schema Abstraction

### Version-Specific Behavior

The RegistryService abstracts differences between registry schema versions:

**v1.1.0 Registry Schema (CrackingShells Format):**
- Repository-based structure with packages containing versions
- Standard package metadata fields
- Version constraint validation

**Future Registry Schemas:**
- Will be handled automatically through the accessor chain
- Backward compatibility maintained through delegation

### Consistent Interface

Regardless of registry schema version, the same method calls work:

```python
# This code works with any supported registry schema version
service = RegistryService(registry_data)
exists = service.package_exists("my-package")
version = service.find_compatible_version("my-package", ">=1.0.0")
uri = service.get_package_uri("my-package", version)
```

## Integration with Chain of Responsibility

### Accessor Chain Creation

When RegistryService loads registry data, it:

1. **Analyzes Data Format**: Examines registry data structure and schema indicators
2. **Creates Chain**: Uses RegistryAccessorFactory to create accessor chain
3. **Links Components**: Accessors are linked to handle format variations
4. **Delegates Requests**: Each accessor handles its format or delegates to compatible accessors

### Delegation Flow

For registry operations:

1. **Primary Accessor**: Attempts to handle the registry data format
2. **Fallback Accessors**: Handle alternative formats or provide compatibility
3. **Service**: Returns unified results to caller

## Error Handling

### Common Exceptions

**RegistryError**: Raised when:
- Registry data is not loaded when accessing operations
- No accessor can handle the registry data format
- Registry operations fail due to data inconsistencies

**VersionConstraintError**: Raised when:
- No package version satisfies the given constraint
- Version constraint format is invalid

### Best Practices

```python
from hatch_validator.registry.registry_service import RegistryService, RegistryError
from hatch_validator.utils.version_utils import VersionConstraintError

try:
    service = RegistryService(registry_data)
    if service.package_exists("my-package"):
        version = service.find_compatible_version("my-package", ">=1.0.0")
        uri = service.get_package_uri("my-package", version)
except RegistryError as e:
    # Handle registry data or loading errors
    print(f"Registry operation failed: {e}")
except VersionConstraintError as e:
    # Handle version constraint errors
    print(f"Version resolution failed: {e}")
```

## Performance Considerations

### Efficient Package Discovery

- Use `package_exists()` before attempting version resolution
- Cache registry service instances when working with the same registry data
- Leverage repository-specific operations when working with known repositories

### Version Resolution Optimization

- Use specific version constraints when possible to reduce resolution time
- Consider caching resolved versions for frequently accessed packages

## Real-World Usage Examples

For comprehensive examples of RegistryService usage in production environments, including integration with dependency orchestrators and environment managers, see [Programmatic Usage](../integration/ProgrammaticUsage.md).

## Related Documentation

- [PackageService Guide](PackageService.md) - Version-agnostic package metadata access
- [Version-Agnostic Access Concepts](VersionAgnosticAccess.md) - Core principles and benefits
- [Chain of Responsibility Pattern](../../devs/architecture/ChainOfResponsibilityPattern.md) - Architectural foundation
- [Programmatic Usage](../integration/ProgrammaticUsage.md) - Real-world integration examples
