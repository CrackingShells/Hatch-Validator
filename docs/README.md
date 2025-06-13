# Hatch-Validator Documentation

Welcome to the Hatch-Validator documentation! This documentation covers the architecture, API, and usage of the Hatch package validation system.

## Table of Contents

### Getting Started
- [Getting Started Guide](getting_started.md) - Quick start guide with examples
- [Installation](getting_started.md#installation) - How to install and set up
- [Common Use Cases](getting_started.md#common-use-cases) - Real-world usage examples

### Architecture & Design
- [Architecture Guide](architecture.md) - Understanding the design patterns
- [Core Components](architecture.md#key-components) - Overview of main components
- [Adding New Schema Versions](architecture.md#adding-a-new-schema-version) - Step-by-step guide
- [Best Practices](architecture.md#best-practices) - Recommended patterns

### API Documentation
- [API Reference](api_reference.md) - Complete API documentation
- [Core Classes](api_reference.md#core-components) - ValidationContext, ValidatorFactory
- [Strategy Interfaces](api_reference.md#strategy-interfaces) - Abstract strategy classes
- [Utility Modules](api_reference.md#utility-modules) - Reusable utility classes

## Quick Reference

### Basic Validation

```python
from hatch_validator import HatchPackageValidator
from pathlib import Path

validator = HatchPackageValidator()
is_valid, errors = validator.validate_package(Path("path/to/package"))
```

### Schema-Specific Validation

```python
from hatch_validator.core.validator_factory import ValidatorFactory

validator = ValidatorFactory.create_validator_chain(target_version="1.1.0")
is_valid, errors = validator.validate(metadata, context)
```

### Using Utility Modules

```python
from hatch_validator.utils.dependency_graph import DependencyGraph
from hatch_validator.utils.version_utils import VersionConstraintValidator

# Check for cycles
graph = DependencyGraph()
has_cycles = graph.has_cycles(adjacency_list)

# Validate version constraints
version_validator = VersionConstraintValidator()
is_valid = version_validator.is_valid_constraint(">=1.0.0")
```

## Architecture Overview

Hatch-Validator uses two main design patterns:

1. **Chain of Responsibility**: Validators are chained by schema version
2. **Strategy Pattern**: Different validation aspects use separate strategies

```
ValidatorFactory → SchemaValidator → Strategies
                      ↓               ↓
                   (v1.2.0)      DependencyValidation
                      ↓          SchemaValidation  
                   (v1.1.0)      EntryPointValidation
                      ↓          ToolsValidation
                    (...)
```

## Key Features

### ✅ Multi-Version Support
- Clean separation between schema versions
- Backward compatibility maintained
- Easy to add new schema versions

### ✅ Modular Design
- Separate strategies for different validation aspects
- Reusable utility modules
- Clear separation of concerns

### ✅ Comprehensive Validation
- JSON schema validation
- Dependency resolution and cycle detection
- Entry point file validation
- Tool configuration validation

### ✅ Flexible Configuration
- Customizable validation contexts
- Support for local and registry dependencies
- Configurable error handling

## Supported Schema Versions

| Version | Status | Features |
|---------|--------|----------|
| v1.1.0  | ✅ Stable | Separate dependency arrays, full validation |
| v1.2.0  | 🚧 Planned | Enhanced dependency syntax, improved tools |

## Contributing

To contribute to Hatch-Validator:

1. Follow the architecture patterns described in this documentation
2. Add comprehensive tests for new features
3. Use the utility modules for common operations
4. Maintain backward compatibility

## Examples

### CI/CD Integration

```bash
# .github/workflows/validate.yml
- name: Validate Package
  run: |
    python -c "
    from hatch_validator import HatchPackageValidator
    from pathlib import Path
    import sys
    
    validator = HatchPackageValidator()
    is_valid, errors = validator.validate_package(Path('.'))
    
    if not is_valid:
        print('Validation failed:')
        for error in errors:
            print(f'  - {error}')
        sys.exit(1)
    print('✓ Package validation passed')
    "
```

### Custom Validation Script

```python
#!/usr/bin/env python3
"""Custom validation with detailed reporting."""

from hatch_validator.core.validator_factory import ValidatorFactory
from hatch_validator.core.validation_context import ValidationContext
from pathlib import Path
import json

def validate_package(package_dir: Path, schema_version: str = None):
    """Validate package with detailed error reporting."""
    
    # Load metadata
    metadata_file = package_dir / "hatch_metadata.json"
    if not metadata_file.exists():
        print(f"❌ No metadata file found at {metadata_file}")
        return False
    
    with open(metadata_file) as f:
        metadata = json.load(f)
    
    # Create context
    context = ValidationContext(
        package_dir=package_dir,
        allow_local_dependencies=True
    )
    
    # Create validator
    validator = ValidatorFactory.create_validator_chain(target_version=schema_version)
    
    # Validate
    is_valid, errors = validator.validate(metadata, context)
    
    if is_valid:
        print("✅ Package validation passed!")
        return True
    else:
        print("❌ Package validation failed:")
        
        # Group errors by type
        error_types = {
            'schema': [],
            'dependency': [],
            'entry_point': [],
            'tools': [],
            'other': []
        }
        
        for error in errors:
            error_lower = error.lower()
            if 'schema' in error_lower:
                error_types['schema'].append(error)
            elif 'dependency' in error_lower or 'circular' in error_lower:
                error_types['dependency'].append(error)
            elif 'entry point' in error_lower:
                error_types['entry_point'].append(error)
            elif 'tool' in error_lower:
                error_types['tools'].append(error)
            else:
                error_types['other'].append(error)
        
        for error_type, type_errors in error_types.items():
            if type_errors:
                print(f"\n{error_type.title()} Errors:")
                for error in type_errors:
                    print(f"  • {error}")
        
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: validate.py <package_directory> [schema_version]")
        sys.exit(1)
    
    package_dir = Path(sys.argv[1])
    schema_version = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = validate_package(package_dir, schema_version)
    sys.exit(0 if success else 1)
```

---

For more detailed information, see the individual documentation files:
- [Getting Started](getting_started.md)
- [Architecture Guide](architecture.md)  
- [API Reference](api_reference.md)
