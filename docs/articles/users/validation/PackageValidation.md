# Package Validation Guide

This article is about:
- Package validation workflow concepts using HatchPackageValidator
- Validation result interpretation and error handling
- Integration with the Chain of Responsibility validation system
- Cross-reference to real-world CLI usage examples

## Overview

Package validation in Hatch-Validator uses the Chain of Responsibility pattern to provide comprehensive validation across different schema versions. The HatchPackageValidator class serves as the main entry point for validation operations, automatically handling schema version detection and delegation.

## Validation Workflow Concepts

### Automatic Schema Version Detection

The HatchPackageValidator automatically detects the package schema version and creates the appropriate validator chain:

```python
from hatch_validator import HatchPackageValidator
from pathlib import Path

# Validator automatically detects and handles schema versions
validator = HatchPackageValidator(
    version="latest",
    allow_local_dependencies=True
)

# Validation works regardless of package schema version
package_path = Path("./my-package")
is_valid, results = validator.validate_package(package_path)
```

### Chain of Responsibility Validation

The validation process follows these steps:

1. **Metadata Loading**: Load package metadata from hatch_metadata.json
2. **Schema Detection**: Extract `package_schema_version` from metadata
3. **Chain Creation**: Create validator chain starting from detected version
4. **Validation Execution**: Execute validation through the chain with delegation
5. **Result Aggregation**: Collect and return comprehensive validation results

### Validation Categories

The validator performs comprehensive validation across multiple categories:

- **Metadata Schema**: Validates metadata structure against schema requirements
- **Entry Points**: Validates entry point configuration and file existence
- **Tools**: Validates tools configuration and requirements
- **Dependencies**: Validates dependency structure and registry availability

## Validation Result Interpretation

### Result Structure

Validation results are returned as a tuple containing:

```python
is_valid, results = validator.validate_package(package_path)

# is_valid: bool - Overall validation success
# results: Dict[str, Any] - Detailed validation results
```

### Result Dictionary Format

The results dictionary contains category-specific validation information:

```python
{
    'valid': bool,                    # Overall validation status
    'metadata_schema': {
        'valid': bool,                # Schema validation status
        'errors': List[str]           # Schema validation errors
    },
    'entry_point': {
        'valid': bool,                # Entry point validation status
        'errors': List[str]           # Entry point validation errors
    },
    'tools': {
        'valid': bool,                # Tools validation status
        'errors': List[str]           # Tools validation errors
    },
    'dependencies': {
        'valid': bool,                # Dependency validation status
        'errors': List[str]           # Dependency validation errors
    },
    'metadata': Dict[str, Any]        # Loaded package metadata
}
```

### Error Handling Patterns

#### Basic Error Handling

```python
is_valid, results = validator.validate_package(package_path)

if not is_valid:
    print("Package validation failed:")
    for category, result in results.items():
        if category not in ['valid', 'metadata'] and isinstance(result, dict):
            if not result.get('valid', True) and result.get('errors'):
                print(f"{category.replace('_', ' ').title()} errors:")
                for error in result['errors']:
                    print(f"  - {error}")
```

#### Category-Specific Error Handling

```python
if not results['metadata_schema']['valid']:
    print("Schema validation failed:")
    for error in results['metadata_schema']['errors']:
        print(f"  Schema error: {error}")

if not results['dependencies']['valid']:
    print("Dependency validation failed:")
    for error in results['dependencies']['errors']:
        print(f"  Dependency error: {error}")
```

## Validator Configuration

### Constructor Parameters

```python
HatchPackageValidator(
    version: str = "latest",
    allow_local_dependencies: bool = True,
    force_schema_update: bool = False,
    registry_data: Optional[Dict] = None
)
```

**Parameters:**
- `version`: Schema version to target ("latest" for newest available)
- `allow_local_dependencies`: Whether to allow local dependency validation
- `force_schema_update`: Whether to force schema cache updates
- `registry_data`: Registry data for dependency validation

### Registry Integration

For dependency validation against registries:

```python
# Validator with registry data for comprehensive dependency validation
validator = HatchPackageValidator(
    version="latest",
    allow_local_dependencies=True,
    registry_data=registry_data  # From environment manager
)
```

## Schema Version Handling

### Version-Specific Validation

The validator automatically handles different schema versions through delegation:

**v1.1.0 Validation:**
- Basic entry point validation
- Separate hatch and python dependency validation
- Standard tools validation

**v1.2.0 Validation:**
- Enhanced dependency structure validation
- Support for hatch, python, system, and docker dependencies
- Delegates entry point and tools validation to v1.1.0

**v1.2.1 Validation:**
- Dual entry point validation (mcp_server and hatch_mcp_server)
- Enhanced tools validation
- Delegates dependency validation to v1.2.0

### Transparent Version Handling

Consumer code remains the same regardless of schema version:

```python
# This validation code works with any supported schema version
validator = HatchPackageValidator()
is_valid, results = validator.validate_package(package_path)
```

## Integration with Chain of Responsibility

### Validator Chain Construction

When validating a package, the system:

1. **Loads Metadata**: Reads hatch_metadata.json from package directory
2. **Detects Version**: Extracts `package_schema_version` from metadata
3. **Creates Chain**: Uses ValidatorFactory to create validator chain
4. **Links Validators**: Each validator points to the next older version
5. **Executes Validation**: Runs validation through the chain with delegation

### Delegation Flow Example

For a v1.2.1 package validation:

1. **v1.2.1 Validator**: Validates dual entry points and tools → delegates dependencies to v1.2.0
2. **v1.2.0 Validator**: Validates unified dependency structure → delegates entry points to v1.1.0
3. **v1.1.0 Validator**: Provides base validation for delegated concerns
4. **Result Aggregation**: Combines validation results from all validators

## Validation Context

### Context Management

The validation system uses ValidationContext to manage state and resources:

- **Registry Data**: Available registry information for dependency validation
- **Local Dependencies**: Configuration for local dependency handling
- **Validation State**: Tracking validation progress and results

### Resource Integration

The validator integrates with external resources:

- **Schema Cache**: Cached schema definitions for validation
- **Registry Service**: Registry data for dependency existence validation
- **File System**: Package files and metadata validation

## Performance Considerations

### Efficient Validation

- **Lazy Loading**: Validators are created only when needed
- **Chain Optimization**: Validation stops at the first capable validator
- **Resource Caching**: Schema and registry data are cached for reuse

### Validation Optimization

- **Early Termination**: Validation can stop on first critical error
- **Parallel Validation**: Independent validation categories can run concurrently
- **Resource Reuse**: Validator instances can be reused for multiple packages

## Real-World Usage Examples

For comprehensive examples of package validation in production environments, including CLI integration and automated validation workflows, see [Programmatic Usage](../integration/ProgrammaticUsage.md).

## Related Documentation

- [Schema Management](SchemaManagement.md) - Schema fetching and version handling
- [Programmatic Usage](../integration/ProgrammaticUsage.md) - Real-world validation examples
- [Chain of Responsibility Pattern](../../devs/architecture/ChainOfResponsibilityPattern.md) - Validation architecture
- [Component Types](../../devs/architecture/ComponentTypes.md) - How validators work with other components
