# Getting Started with Hatch-Validator

## Installation

Hatch-Validator is part of the Hatch ecosystem. Install it using pip:

```bash
pip install git+htt
```

## Quick Start

### Basic Package Validation

```python
from hatch_validator import HatchPackageValidator
from pathlib import Path

# Create a validator instance
validator = HatchPackageValidator()

# Validate a package directory
package_dir = Path("path/to/your/package")
is_valid, errors = validator.validate_package(package_dir)

if is_valid:
    print("✓ Package validation passed!")
else:
    print("✗ Package validation failed:")
    for error in errors:
        print(f"  - {error}")
```

### Validating Specific Schema Versions

```python
from hatch_validator.core.validator_factory import ValidatorFactory
from hatch_validator.core.validation_context import ValidationContext
import json

# Load package metadata
with open("hatch_metadata.json") as f:
    metadata = json.load(f)

# Create validation context
context = ValidationContext(
    package_dir=Path("path/to/package"),
    allow_local_dependencies=True
)

# Create validator for specific schema version
validator = ValidatorFactory.create_validator_chain(target_version="1.1.0")

# Validate
is_valid, errors = validator.validate(metadata, context)
```

## Common Use Cases

### 1. CI/CD Pipeline Integration

```python
#!/usr/bin/env python3
"""Package validation script for CI/CD pipeline."""

import sys
from pathlib import Path
from hatch_validator import HatchPackageValidator

def main():
    if len(sys.argv) != 2:
        print("Usage: validate.py <package_directory>")
        sys.exit(1)
    
    package_dir = Path(sys.argv[1])
    validator = HatchPackageValidator()
    
    is_valid, errors = validator.validate_package(package_dir)
    
    if is_valid:
        print("✓ Package validation passed")
        sys.exit(0)
    else:
        print("✗ Package validation failed:")
        for error in errors:
            print(f"  {error}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### 2. Validating with Custom Registry Data

```python
from hatch_validator.core.validation_context import ValidationContext
from hatch_validator.core.validator_factory import ValidatorFactory
import json

# Load custom registry data
with open("custom_registry.json") as f:
    registry_data = json.load(f)

# Create context with custom registry
context = ValidationContext(
    package_dir=Path("path/to/package"),
    registry_data=registry_data,
    allow_local_dependencies=False  # Stricter validation
)

# Validate using latest schema version
validator = ValidatorFactory.create_validator_chain()
is_valid, errors = validator.validate(metadata, context)
```

### 3. Dependency-Only Validation

```python
from hatch_validator.schemas.v1_1_0.dependency_validation_strategy import DependencyValidationV1_1_0
from hatch_validator.core.validation_context import ValidationContext

# Create dependency validation strategy
dep_validator = DependencyValidationV1_1_0()

# Validate only dependencies
context = ValidationContext(package_dir=Path("path/to/package"))
is_valid, errors = dep_validator.validate_dependencies(metadata, context)
```

## Understanding Validation Results

### Success Case

```python
is_valid, errors = validator.validate_package(package_dir)
# is_valid: True
# errors: []
```

### Failure Cases

```python
is_valid, errors = validator.validate_package(package_dir)
# is_valid: False
# errors: [
#     "Entry point file 'main.py' does not exist",
#     "Dependency 'non_existent_pkg' not found in registry",
#     "Circular dependency detected: pkg_a -> pkg_b -> pkg_a"
# ]
```

## Error Types

### Schema Validation Errors

These occur when metadata doesn't conform to the JSON schema:

```
- Missing required field 'name'
- Invalid value for field 'version': must be a valid semantic version
- Additional property 'unknown_field' not allowed
```

### Dependency Validation Errors

These occur when there are issues with package dependencies:

```
- Dependency 'missing_pkg' not found in registry
- Invalid version constraint '>>1.0.0' for package 'my_pkg'
- Circular dependency detected: pkg_a -> pkg_b -> pkg_a
- Local dependency 'local_pkg' not allowed in this context
```

### Entry Point Validation Errors

These occur when entry point files are missing or invalid:

```
- Entry point file 'main.py' does not exist
- Entry point 'main.py' is not a valid Python file
- Entry point directory 'src' is not a file
```

### Tools Validation Errors

These occur when tool configurations are invalid:

```
- Tool 'my_tool' entry point 'tool_main.py' does not exist
- Invalid tool configuration for 'my_tool'
```

## Configuration Options

### ValidationContext Parameters

```python
context = ValidationContext(
    package_dir=Path("path/to/package"),      # Required: package directory
    registry_data=registry_data,              # Optional: custom registry data
    allow_local_dependencies=True,            # Optional: allow local deps (default: True)
    force_schema_update=False                 # Optional: force schema cache update (default: False)
)
```

### Validator Factory Options

```python
# Create validator for specific version
validator = ValidatorFactory.create_validator_chain(target_version="1.1.0")

# Create validator for latest version (default)
validator = ValidatorFactory.create_validator_chain()

# Create validator with fallback chain
validator = ValidatorFactory.create_validator_chain()  # Will try v1.2.0 -> v1.1.0 -> ...
```

## Best Practices

### 1. Use Appropriate Context Settings

```python
# For production packages (stricter validation)
context = ValidationContext(
    package_dir=package_dir,
    registry_data=production_registry,
    allow_local_dependencies=False
)

# For development packages (more permissive)
context = ValidationContext(
    package_dir=package_dir,
    allow_local_dependencies=True
)
```

### 2. Handle Errors Gracefully

```python
try:
    is_valid, errors = validator.validate_package(package_dir)
    
    if not is_valid:
        # Group errors by type for better reporting
        schema_errors = [e for e in errors if "schema" in e.lower()]
        dep_errors = [e for e in errors if "dependency" in e.lower()]
        
        if schema_errors:
            print("Schema validation errors:")
            for error in schema_errors:
                print(f"  - {error}")
        
        if dep_errors:
            print("Dependency validation errors:")
            for error in dep_errors:
                print(f"  - {error}")
                
except Exception as e:
    print(f"Validation failed with exception: {e}")
```

### 3. Cache Registry Data

```python
import json
from pathlib import Path

# Load and cache registry data
registry_cache_file = Path("registry_cache.json")

if registry_cache_file.exists():
    with open(registry_cache_file) as f:
        registry_data = json.load(f)
else:
    # Fetch from remote and cache
    registry_data = fetch_remote_registry()
    with open(registry_cache_file, 'w') as f:
        json.dump(registry_data, f)

# Use cached data for validation
context = ValidationContext(
    package_dir=package_dir,
    registry_data=registry_data
)
```

### 4. Integrate with Build Tools

#### With setuptools

```python
# setup.py
from setuptools import setup
from setuptools.command.build_py import build_py
from hatch_validator import HatchPackageValidator

class ValidatedBuild(build_py):
    def run(self):
        # Validate before building
        validator = HatchPackageValidator()
        is_valid, errors = validator.validate_package(Path("."))
        
        if not is_valid:
            print("Package validation failed:")
            for error in errors:
                print(f"  - {error}")
            raise RuntimeError("Package validation failed")
        
        super().run()

setup(
    # ... other setup parameters ...
    cmdclass={'build_py': ValidatedBuild}
)
```

#### With pytest

```python
# test_package_validation.py
import pytest
from pathlib import Path
from hatch_validator import HatchPackageValidator

def test_package_validation():
    """Test that the package passes validation."""
    validator = HatchPackageValidator()
    package_dir = Path(__file__).parent.parent  # Adjust path as needed
    
    is_valid, errors = validator.validate_package(package_dir)
    
    if not is_valid:
        pytest.fail(f"Package validation failed: {errors}")
```

## Troubleshooting

### Common Issues

#### 1. "Schema file not found"

This usually means the schema cache is corrupted or missing:

```python
# Force schema update
context = ValidationContext(
    package_dir=package_dir,
    force_schema_update=True
)
```

#### 2. "Cannot import name 'ValidationStrategy'"

This suggests a version mismatch. Ensure you're using compatible versions:

```bash
pip install --upgrade hatch-validator
```

#### 3. "Registry data not available"

When working offline or with custom registries:

```python
# Load local registry data
with open("local_registry.json") as f:
    registry_data = json.load(f)

context = ValidationContext(
    package_dir=package_dir,
    registry_data=registry_data
)
```

### Debugging Validation

Enable detailed logging to understand what's happening:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("hatch")

# Now run validation - you'll see detailed logs
is_valid, errors = validator.validate_package(package_dir)
```

## Next Steps

- Read the [Architecture Guide](architecture.md) to understand the internal design
- Check the [API Reference](api_reference.md) for detailed API documentation
- Learn how to [add new schema versions](architecture.md#adding-a-new-schema-version)
- Explore the utility modules for advanced usage
