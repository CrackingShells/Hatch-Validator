# Hatch-Validator Architecture Guide

## Overview

Hatch-Validator uses a modular, extensible architecture based on the **Chain of Responsibility** and **Strategy** design patterns. This architecture allows for easy addition of new schema versions while maintaining backward compatibility and clear separation of concerns.

## Core Architecture Patterns

### Chain of Responsibility Pattern

The validator system uses a chain of validators where each validator handles a specific schema version. When a package needs validation, the request flows through the chain until a validator that can handle the specific schema version is found.

```
Request → V1.2.0 Validator → V1.1.0 Validator → ... → Default Handler
                ↓
           (can handle?)
                ↓
            Validation Logic
```

### Strategy Pattern

Each validator uses multiple strategy objects to handle different aspects of validation:

- **SchemaValidationStrategy**: Validates metadata against JSON schema
- **DependencyValidationStrategy**: Validates package dependencies
- **EntryPointValidationStrategy**: Validates entry point files
- **ToolsValidationStrategy**: Validates tool configurations

## Directory Structure

```
hatch_validator/
├── core/                           # Core framework components
│   ├── validation_context.py      # Shared validation context
│   ├── validator_base.py           # Abstract validator base class
│   ├── validation_strategy.py     # Abstract strategy interfaces
│   └── validator_factory.py       # Factory for creating validators
├── utils/                          # Reusable utility modules
│   ├── dependency_graph.py        # Graph operations (cycles, paths)
│   ├── version_utils.py           # Version constraint validation
│   └── registry_client.py         # Registry interaction abstractions
├── schemas/
│   ├── v1_1_0/                    # v1.1.0 schema implementation
│   │   ├── schema_validators.py    # Schema-specific validator
│   │   ├── dependency_validation_strategy.py  # Dependency validation
│   │   └── legacy_dependency_validation.py    # Legacy implementation
│   └── v1_2_0/                    # v1.2.0 schema implementation (future)
└── package_validator.py           # Main public interface
```

## Key Components

### 1. ValidationContext

The `ValidationContext` class carries shared state and resources throughout the validation process:

```python
from hatch_validator.core.validation_context import ValidationContext

context = ValidationContext(
    package_dir=package_path,
    registry_data=registry_data,
    allow_local_dependencies=True
)
```

### 2. Validator Factory

The `ValidatorFactory` creates the appropriate validator chain:

```python
from hatch_validator.core.validator_factory import ValidatorFactory

# Create validator for specific version
validator = ValidatorFactory.create_validator_chain(target_version="1.1.0")

# Create validator for latest version (default)
validator = ValidatorFactory.create_validator_chain()
```

### 3. Strategy Implementations

Each strategy handles a specific aspect of validation:

```python
# Example: Dependency validation strategy
class DependencyValidationV1_1_0(DependencyValidationStrategy):
    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        # Implementation specific to v1.1.0 dependency format
        pass
```

## Adding a New Schema Version

Follow these steps to add support for a new schema version (e.g., v1.2.0):

### Step 1: Create Schema Directory

```bash
mkdir hatch_validator/schemas/v1_2_0
```

### Step 2: Implement Validation Strategies

Create strategy implementations for the new schema version:

```python
# hatch_validator/schemas/v1_2_0/dependency_validation_strategy.py
from hatch_validator.core.validation_strategy import DependencyValidationStrategy
from hatch_validator.utils.dependency_graph import DependencyGraph
from hatch_validator.utils.version_utils import VersionConstraintValidator
from hatch_validator.utils.registry_client import RegistryClient

class DependencyValidationV1_2_0(DependencyValidationStrategy):
    """Dependency validation strategy for v1.2.0 schema."""
    
    def __init__(self):
        self.dependency_graph = DependencyGraph()
        self.version_validator = VersionConstraintValidator()
        self.registry_client = RegistryClient()
    
    def validate_dependencies(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        # Extract dependencies in v1.2.0 format
        dependencies = self._extract_v1_2_0_dependencies(metadata)
        
        # Use utility modules for validation logic
        graph = self.dependency_graph.create_graph(dependencies)
        has_cycles = self.dependency_graph.has_cycles(graph)
        
        # Return validation results
        return not has_cycles, [] if not has_cycles else ["Circular dependency detected"]
    
    def _extract_v1_2_0_dependencies(self, metadata: Dict) -> List[Dict]:
        # Implement v1.2.0-specific dependency extraction
        pass
```

### Step 3: Create Schema Validator

```python
# hatch_validator/schemas/v1_2_0/schema_validators.py
from hatch_validator.core.validator_base import SchemaValidator
from .dependency_validation_strategy import DependencyValidationV1_2_0

class SchemaValidator(SchemaValidator):
    """Validator for schema version 1.2.0."""
    
    def __init__(self, next_validator=None):
        super().__init__(next_validator)
        self.dependency_strategy = DependencyValidationV1_2_0()
        # Initialize other strategies...
    
    def can_handle(self, schema_version: str) -> bool:
        return schema_version == "1.2.0"
    
    def validate(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        # Implement validation logic using strategies
        pass
```

### Step 4: Update Validator Factory

```python
# hatch_validator/core/validator_factory.py
def create_validator_chain(target_version: Optional[str] = None) -> SchemaValidator:
    # Import new validator
    from hatch_validator.schemas.v1_2_0.schema_validators import SchemaValidator as V120Validator
    from hatch_validator.schemas.v1_1_0.schema_validators import SchemaValidator as V110Validator
    
    # Create validators (newest to oldest)
    v1_2_0_validator = V120Validator()
    v1_1_0_validator = V110Validator()
    
    # Set up chain
    v1_2_0_validator.set_next(v1_1_0_validator)
    
    # Return appropriate validator based on target version
    if target_version == "1.2.0":
        return v1_2_0_validator
    elif target_version == "1.1.0":
        return v1_1_0_validator
    elif target_version is None:
        # Default to latest version
        return v1_2_0_validator
    else:
        raise ValueError(f"Unsupported schema version: {target_version}")
```

### Step 5: Create Tests

```python
# tests/test_schema_validators_v1_2_0.py
import unittest
from hatch_validator.schemas.v1_2_0.schema_validators import SchemaValidator

class TestSchemaV1_2_0Validator(unittest.TestCase):
    def test_can_handle_v1_2_0(self):
        validator = SchemaValidator()
        self.assertTrue(validator.can_handle("1.2.0"))
    
    def test_validation_with_v1_2_0_metadata(self):
        # Test v1.2.0 specific functionality
        pass
```

## Utility Modules

The architecture includes reusable utility modules that can be used across different schema versions:

### DependencyGraph

Handles graph operations for dependency analysis:

```python
from hatch_validator.utils.dependency_graph import DependencyGraph

graph = DependencyGraph()
adjacency_list = graph.create_adjacency_list(dependencies)
has_cycles = graph.has_cycles(adjacency_list)
cycles = graph.find_cycles(adjacency_list)
```

### VersionConstraintValidator

Validates and parses version constraints:

```python
from hatch_validator.utils.version_utils import VersionConstraintValidator

validator = VersionConstraintValidator()
is_valid = validator.is_valid_constraint(">=1.0.0")
is_compatible = validator.is_compatible("1.5.0", ">=1.0.0")
```

### RegistryClient

Provides abstraction for registry interactions:

```python
from hatch_validator.utils.registry_client import RegistryClient

client = RegistryClient(registry_data)
package_exists = client.package_exists("my_package")
versions = client.get_package_versions("my_package")
```

## Best Practices

### 1. Use Utility Modules

Always leverage the utility modules for common operations rather than reimplementing logic:

```python
# Good
from hatch_validator.utils.dependency_graph import DependencyGraph
graph = DependencyGraph()
has_cycles = graph.has_cycles(adjacency_list)

# Bad - reimplementing cycle detection
def detect_cycles(dependencies):
    # Custom cycle detection logic
    pass
```

### 2. Follow the Strategy Pattern

Each validation aspect should be handled by a separate strategy:

```python
# Good - separate strategies
class SchemaValidator(SchemaValidator):
    def __init__(self):
        self.schema_strategy = SchemaValidationV1_2_0()
        self.dependency_strategy = DependencyValidationV1_2_0()
        self.entry_point_strategy = EntryPointValidationV1_2_0()

# Bad - monolithic validator
class SchemaValidator(SchemaValidator):
    def validate(self, metadata, context):
        # All validation logic in one method
        pass
```

### 3. Maintain Chain Order

Always order validators from newest to oldest in the chain:

```python
# Correct order: v1.2.0 → v1.1.0 → ...
v1_2_0_validator.set_next(v1_1_0_validator)

# Wrong order: v1.1.0 → v1.2.0
v1_1_0_validator.set_next(v1_2_0_validator)  # This would prevent v1.2.0 from being reached
```

### 4. Use Proper Error Handling

Return meaningful error messages that help users understand what went wrong:

```python
def validate_dependencies(self, metadata, context):
    errors = []
    
    # Specific, actionable error messages
    if not dependencies:
        errors.append("No dependencies found - at least one dependency is required")
    
    for dep in dependencies:
        if not dep.get('name'):
            errors.append(f"Dependency missing name: {dep}")
    
    return len(errors) == 0, errors
```

## Testing Strategy

The architecture supports comprehensive testing at multiple levels:

### Unit Tests
- Test individual utility modules in isolation
- Test strategy implementations independently
- Mock external dependencies (registry, file system)

### Integration Tests
- Test complete validator chains
- Compare new implementations with legacy ones
- Test with real package metadata

### Comparison Tests
- When adding new implementations, compare results with existing ones
- Ensure backward compatibility is maintained

## Migration Guide

When updating from the old architecture:

1. **Identify Dependencies**: Use utility modules instead of custom implementations
2. **Split Concerns**: Separate different validation aspects into strategies
3. **Update Tests**: Create comparison tests to ensure no regression
4. **Gradual Migration**: Keep legacy implementations for comparison during transition

This architecture provides a solid foundation for maintaining and extending the Hatch-Validator system while ensuring code quality and ease of development.
