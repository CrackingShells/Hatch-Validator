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
pip install git+https://github.com/CrackingShells/Hatch-Validator.git

# Or install local copy
pip install /path/to/Hatch-Validator
```

### As a Submodule

If using as a git submodule:

1. Add as a submodule to your project:

   ```bash
   git submodule add https://github.com/CrackingShells/Hatch-Validator.git validator
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

## Contributing

We welcome contributions! Please see our [Contributing Guide](./CONTRIBUTING.md) for details.

### Quick Start

1. **Fork and clone** the repository
2. **Install dependencies**: `pip install -e .` and `npm install`
3. **Create a feature branch**: `git checkout -b feat/your-feature`
4. **Make changes** and add tests
5. **Use conventional commits**: `npm run commit` for guided commits
6. **Run tests**: `python -c "import hatch_validator; print('Package imports successfully')"`
7. **Create a pull request**

### Commit Messages

We use [Conventional Commits](https://www.conventionalcommits.org/) for automated versioning:

```bash
feat: add new feature
fix: resolve bug
docs: update documentation
test: add tests
chore: maintenance tasks
```

Use `npm run commit` for guided commit messages.

For detailed guidelines, see [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

AGPL v3: see [file](./LICENSE)