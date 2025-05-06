# Hatch-Validator

A validation package for Hatch packages and dependencies.

## Features

- **Package Validation**: Validate Hatch packages against schema specifications
- **Dependency Resolution**: Resolve and validate package dependencies
- **Schema Management**: Automatically fetch and manage schema versions

## Installation

### From Source

```bash
# Install directly from the repository
pip install git+https://github.com/yourusername/Hatch-Validator.git

# Or install local copy
pip install /path/to/Hatch-Validator
```

### As a Submodule

If using as a git submodule:

1. Add as a submodule to your project:
   ```bash
   git submodule add https://github.com/yourusername/Hatch-Validator.git validator
   ```

2. Install the submodule as a package:
   ```bash
   pip install ./validator
   ```

## Usage

```python
from hatch_validator import HatchPackageValidator, DependencyResolver

# Initialize validator
validator = HatchPackageValidator()

# Validate a package
is_valid, results = validator.validate_package('/path/to/package')
if is_valid:
    print("Package is valid!")
else:
    print("Validation errors:", results)

# Initialize dependency resolver
resolver = DependencyResolver()

# Check for missing dependencies
missing_deps = resolver.get_missing_hatch_dependencies(dependencies)
```

## License

AGPL v3: see [file](./LICENSE)