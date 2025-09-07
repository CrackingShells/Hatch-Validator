# Getting Started with Hatch-Validator

This article is about:
- Installing and setting up Hatch-Validator
- Understanding version-agnostic data access concepts
- Basic validation workflows using HatchPackageValidator
- Introduction to PackageService and RegistryService capabilities

## Installation

Install Hatch-Validator using pip:

```bash
pip install hatch-validator
```

## Core Concepts

### Version-Agnostic Data Access

Hatch-Validator provides a unified interface for working with package metadata and registry data across different schema versions. This means your code remains stable even as package schemas evolve from v1.1.0 to v1.2.0 to v1.2.1 and beyond.

**Key Benefits:**
- **Schema Transparency**: Your code doesn't need to know about schema versions
- **Automatic Evolution**: New schema versions work without code changes
- **Consistent APIs**: Same method signatures across all schema versions

### Chain of Responsibility Architecture

The validator uses the Chain of Responsibility design pattern to handle different schema versions. When you request data or validation, the system automatically:

1. Detects the schema version from metadata
2. Creates the appropriate chain of components
3. Delegates requests through the chain
4. Returns results using a consistent interface

## Basic Package Validation

### Simple Validation Example

```python
from pathlib import Path
from hatch_validator import HatchPackageValidator

# Create validator with default settings
validator = HatchPackageValidator(
    version="latest",
    allow_local_dependencies=True
)

# Validate a package
package_path = Path("./my-package")
is_valid, results = validator.validate_package(package_path)

if is_valid:
    print("Package validation successful!")
else:
    print("Package validation failed:")
    for category, result in results.items():
        if not result.get('valid', True) and result.get('errors'):
            print(f"{category}: {result['errors']}")
```

### Validation with Registry Data

```python
from hatch_validator import HatchPackageValidator

# Create validator with registry data for dependency validation
validator = HatchPackageValidator(
    version="latest",
    allow_local_dependencies=True,
    registry_data=registry_data  # From environment manager
)

# Validation automatically handles schema versions
is_valid, results = validator.validate_package(package_path)
```

## Working with Package Metadata

### PackageService Overview

The PackageService class provides version-agnostic access to package metadata:

```python
from hatch_validator.package.package_service import PackageService

# Load package metadata
service = PackageService(metadata)

# Access dependencies without knowing schema version
dependencies = service.get_dependencies()

# Access any metadata field
name = service.get_field('name')
version = service.get_field('version')
```

**Key Features:**
- Automatic schema version detection
- Unified dependency access across schema versions
- Consistent field access methods

## Working with Registry Data

### RegistryService Overview

The RegistryService class provides version-agnostic access to registry data:

```python
from hatch_validator.registry.registry_service import RegistryService

# Initialize with registry data
service = RegistryService(registry_data)

# Check package existence
exists = service.package_exists("my-package")

# Find compatible versions
compatible_version = service.find_compatible_version(
    "my-package", ">=1.0.0"
)

# Get package URI
uri = service.get_package_uri("my-package", "1.2.0")
```

**Key Features:**
- Automatic registry schema detection
- Version-agnostic package discovery
- Consistent registry operations

## Schema Version Support

Hatch-Validator currently supports these package schema versions:

- **v1.1.0**: Base schema with separate hatch and python dependencies
- **v1.2.0**: Unified dependencies structure with hatch, python, system, and docker support
- **v1.2.1**: Dual entry point support with enhanced validation

The system automatically detects and handles the appropriate schema version based on the `package_schema_version` field in your metadata.

## Integration Patterns

### Environment Integration

For comprehensive examples of how to integrate Hatch-Validator with environment managers, dependency orchestrators, and CLI tools, see [Programmatic Usage](../integration/ProgrammaticUsage.md).

### Data Access Patterns

For detailed information about version-agnostic data access:
- [PackageService Guide](../data_access/PackageService.md)
- [RegistryService Guide](../data_access/RegistryService.md)
- [Version-Agnostic Access Concepts](../data_access/VersionAgnosticAccess.md)

### Validation Workflows

For advanced validation scenarios:
- [Package Validation Guide](../validation/PackageValidation.md)
- [Schema Management](../validation/SchemaManagement.md)

## Next Steps

1. **Explore Real-World Examples**: See [Programmatic Usage](../integration/ProgrammaticUsage.md) for actual integration patterns from first-party consumers
2. **Understand the Architecture**: Read about the [Chain of Responsibility Pattern](../../devs/architecture/ChainOfResponsibilityPattern.md) that enables version-agnostic access
3. **Learn Extension Patterns**: See [Extending Chain of Responsibility](../../devs/contribution_guidelines/ExtendingChainOfResponsibility.md) for adding new schema versions

The version-agnostic design ensures your integration code remains stable as the Hatch ecosystem evolves, providing a reliable foundation for package management and validation workflows.
