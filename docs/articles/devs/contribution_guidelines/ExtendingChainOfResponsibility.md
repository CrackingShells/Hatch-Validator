# Extending Chain of Responsibility

This article is about:

- Adding new schema version support across all three component types
- Extension mechanisms for validators, package accessors, and registry accessors
- Best practices for implementing delegation and maintaining chain integrity
- Testing strategies for new components and chain behavior

## Overview

Extending Hatch-Validator to support new schema versions requires implementing components across all three types: validators, package accessors, and registry accessors. This guide provides comprehensive instructions for adding new schema version support while maintaining the Chain of Responsibility pattern integrity.

## Adding New Schema Version Support

### Step 1: Create Version Directory Structure

For a new schema version (e.g., v1.3.0), create the following directory structure:

```plaintext
hatch_validator/
├── package/
│   └── v1_3_0/
│       ├── __init__.py
│       ├── accessor.py          # Package accessor implementation
│       ├── new_feature_validation.py  # Strategy for new feature validation
│       └── validator.py         # Validator implementation
└── registry/
    └── v1_3_0/
        ├── __init__.py
        └── registry_accessor.py  # Registry accessor implementation
```

### Step 2: Implement Package Accessor

Create the package accessor for the new schema version:

```python
# hatch_validator/package/v1_3_0/accessor.py
from typing import Dict, Any, Optional
from hatch_validator.core.pkg_accessor_base import HatchPkgAccessorBase

class V130PackageAccessor(HatchPkgAccessorBase):
    """Package accessor for schema version 1.3.0."""
    
    def can_handle(self, schema_version: str) -> bool:
        """Check if this accessor can handle the schema version."""
        return schema_version in ["1.3.0", "v1.3.0"]
    
    def get_new_feature(self, metadata: Dict[str, Any]) -> Any:
        """Handle v1.3.0-specific new feature."""
        # Implement new functionality specific to v1.3.0
        return metadata.get('new_feature_field', {})
    
    def get_dependencies(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Delegate dependency access to v1.2.1."""
        # v1.3.0 doesn't change dependency structure, delegate to v1.2.1
        if self.next_accessor:
            return self.next_accessor.get_dependencies(metadata)
        raise NotImplementedError("Dependencies accessor not implemented")
    
    def get_entry_points(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle entry points - may delegate or implement new logic."""
        # If v1.3.0 changes entry point structure, implement here
        # Otherwise, delegate to previous version
        if self.next_accessor:
            return self.next_accessor.get_entry_points(metadata)
        raise NotImplementedError("Entry points accessor not implemented")
```

### Step 3: Implement Validator

Create the validator for the new schema version:

```python
# hatch_validator/package/v1_3_0/validator.py
from typing import Dict, List, Tuple, Optional
from hatch_validator.core.validator_base import Validator
from hatch_validator.core.validation_context import ValidationContext

class V130Validator(Validator):
    """Validator for schema version 1.3.0."""
    
    def can_handle(self, schema_version: str) -> bool:
        """Check if this validator can handle the schema version."""
        return schema_version in ["1.3.0", "v1.3.0"]
    
    def validate(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate v1.3.0 package or delegate to next validator."""
        
        schema_version = metadata.get("package_schema_version", "")
        
        if not self.can_handle(schema_version):
            # Delegate to next validator in chain
            if self.next_validator:
                return self.next_validator.validate(metadata, context)
            return False, [f"Unsupported schema version: {schema_version}"]
        
        # Perform v1.3.0-specific validation
        errors = []
        
        # Validate new features specific to v1.3.0
        new_feature_valid, new_feature_errors = self._validate_new_feature(metadata, context)
        errors.extend(new_feature_errors)
        
        # Delegate unchanged validation concerns to previous validators
        if self.next_validator:
            # Delegate dependency validation to v1.2.1
            dep_valid, dep_errors = self.next_validator.validate_dependencies(metadata, context)
            errors.extend(dep_errors)
            
            # Delegate entry point validation to v1.2.1
            entry_valid, entry_errors = self.next_validator.validate_entry_points(metadata, context)
            errors.extend(entry_errors)
        
        return len(errors) == 0, errors
    
    def _validate_new_feature(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate v1.3.0-specific new feature."""
        errors = []
        
        new_feature = metadata.get('new_feature_field')
        if new_feature is not None:
            # Implement validation logic for new feature
            if not isinstance(new_feature, dict):
                errors.append("new_feature_field must be a dictionary")
            
            # Add more specific validation rules
            required_fields = ['field1', 'field2']
            for field in required_fields:
                if field not in new_feature:
                    errors.append(f"new_feature_field missing required field: {field}")
        
        return len(errors) == 0, errors
```

### Step 4: Implement Registry Accessor (if needed)

If the new schema version affects registry operations, implement a registry accessor:

```python
# hatch_validator/registry/v1_3_0/registry_accessor.py
from typing import Dict, Any, Optional
from hatch_validator.registry.registry_accessor_base import RegistryAccessorBase

class V130RegistryAccessor(RegistryAccessorBase):
    """Registry accessor for schema version 1.3.0."""
    
    def can_handle(self, registry_data: Dict[str, Any]) -> bool:
        """Check if this accessor can handle the registry data."""
        schema_version = registry_data.get('registry_schema_version', '')
        return schema_version.startswith('1.3.')
    
    def package_exists(self, registry_data: Dict[str, Any], package_name: str, 
                      repo_name: Optional[str] = None) -> bool:
        """Check package existence with v1.3.0 registry format."""
        
        # If v1.3.0 doesn't change registry structure, delegate
        if self._successor:
            return self._successor.package_exists(registry_data, package_name, repo_name)
        
        # Otherwise, implement v1.3.0-specific logic here
        return False
```

### Step 5: Register Components with Factories

Update factory classes to register new components:

```python
# hatch_validator/core/pkg_accessor_factory.py
class HatchPkgAccessorFactory:
    @classmethod
    def _ensure_accessors_loaded(cls) -> None:
        """Load all available accessors including v1.3.0."""
        if not cls._accessor_registry:
            # Register v1.3.0 accessor (newest first)
            from hatch_validator.package.v1_3_0.accessor import V130PackageAccessor
            cls.register_accessor('1.3.0', V130PackageAccessor)
            
            # Register existing accessors
            from hatch_validator.package.v1_2_1.accessor import V121PackageAccessor
            cls.register_accessor('1.2.1', V121PackageAccessor)
            
            # ... register other versions
            
            # Update version order (newest to oldest)
            cls._version_order = ['1.3.0', '1.2.1', '1.2.0', '1.1.0']

# hatch_validator/core/validator_factory.py
class ValidatorFactory:
    @classmethod
    def _ensure_validators_loaded(cls) -> None:
        """Load all available validators including v1.3.0."""
        if not cls._validator_registry:
            # Register v1.3.0 validator (newest first)
            from hatch_validator.package.v1_3_0.validator import V130Validator
            cls.register_validator('1.3.0', V130Validator)
            
            # Register existing validators
            # ... register other versions
            
            # Update version order (newest to oldest)
            cls._version_order = ['1.3.0', '1.2.1', '1.2.0', '1.1.0']
```

## Strategy Implementation Guidelines

### When to Implement New Strategies

**Create New Strategy When**:

1. Schema version introduces new validation requirements
2. Validation algorithm changes significantly
3. New validation logic cannot reuse previous implementation

**Use Chain Delegation When**:

1. Validation logic unchanged from previous version
2. Previous version's strategy is sufficient
3. No new validation requirements

### Strategy Implementation Process

1. **Create Strategy Class**:

```python
class NewFeatureValidation(ValidationStrategy):
    def validate_new_feature(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        # Implement v1.3.0-specific validation logic
        pass
```

2. **Compose Strategy in Validator**:

```python
class V130Validator(ValidatorBase):
    def __init__(self, next_validator=None):
        super().__init__(next_validator)
        self.new_feature_strategy = NewFeatureValidation()

    def validate_new_feature(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        return self.new_feature_strategy.validate_new_feature(metadata, context)
```

For comprehensive information on strategy interfaces and patterns, see [Chain of Responsibility Pattern](../architecture/ChainOfResponsibilityPattern.md#strategy-interface-hierarchy).

## Extension Best Practices

For delegation principles and patterns, see [Chain of Responsibility Pattern](../architecture/ChainOfResponsibilityPattern.md#delegation-mechanisms). This section focuses on extension-specific implementation details.

### Error Handling

**Graceful Delegation**: Handle errors gracefully when delegating:

```python
def get_field_with_fallback(self, metadata: Dict[str, Any], field_name: str) -> Any:
    """Get field with graceful delegation."""
    try:
        # Try to handle with this accessor
        if field_name in self.HANDLED_FIELDS:
            return self._get_field(metadata, field_name)
    except Exception as e:
        logger.warning(f"Error handling {field_name}: {e}")
    
    # Delegate to next accessor
    if self.next_accessor:
        return self.next_accessor.get_field_with_fallback(metadata, field_name)
    
    raise NotImplementedError(f"Field {field_name} not handled by any accessor")
```

**Chain Validation**: Validate chain integrity during construction:

```python
def validate_chain_integrity(chain_head: ComponentBase) -> bool:
    """Validate that chain covers all required functionality."""
    
    current = chain_head
    covered_versions = set()
    
    while current:
        # Check that component implements required methods
        required_methods = ['can_handle', 'get_dependencies', 'get_entry_points']
        for method in required_methods:
            if not hasattr(current, method):
                logger.error(f"Component {current.__class__.__name__} missing method: {method}")
                return False
        
        # Track covered versions
        if hasattr(current, 'SUPPORTED_VERSION'):
            covered_versions.add(current.SUPPORTED_VERSION)
        
        current = getattr(current, 'next_accessor', None) or getattr(current, 'next_validator', None)
    
    # Ensure all required versions are covered
    required_versions = {'1.1.0', '1.2.0', '1.2.1'}
    if not required_versions.issubset(covered_versions):
        missing = required_versions - covered_versions
        logger.error(f"Chain missing support for versions: {missing}")
        return False
    
    return True
```

## Maintaining Chain Integrity

### Version Ordering

Maintain correct version ordering in factories:

```python
# Always order from newest to oldest
_version_order = ['1.3.0', '1.2.1', '1.2.0', '1.1.0']

# Verify ordering is correct
def validate_version_ordering(versions: List[str]) -> bool:
    """Validate that versions are ordered newest to oldest."""
    for i in range(len(versions) - 1):
        current = parse_version(versions[i])
        next_version = parse_version(versions[i + 1])
        if current <= next_version:
            return False
    return True
```

### Component Registration

Ensure all components are registered correctly:

```python
def register_all_components():
    """Register all components with their factories."""
    
    # Package accessors
    HatchPkgAccessorFactory.register_accessor('1.3.0', V130PackageAccessor)
    HatchPkgAccessorFactory.register_accessor('1.2.1', V121PackageAccessor)
    # ... register all versions
    
    # Validators
    ValidatorFactory.register_validator('1.3.0', V130Validator)
    ValidatorFactory.register_validator('1.2.1', V121Validator)
    # ... register all versions
    
    # Registry accessors (if applicable)
    RegistryAccessorFactory.register_accessor('1.3.0', V130RegistryAccessor)
    # ... register all versions
```

### Backward Compatibility

Ensure new components maintain backward compatibility:

```python
def test_backward_compatibility():
    """Test that new components work with older packages."""
    
    # v1.3.0 chain should handle v1.2.1 packages
    chain = HatchPkgAccessorFactory.create_accessor_chain("1.3.0")
    
    v121_metadata = {
        "package_schema_version": "1.2.1",
        "name": "old-package",
        "mcp_server": {"command": "server"},
        "hatch_mcp_server": {"command": "hatch-server"}
    }
    
    # Should delegate to v1.2.1 accessor
    entry_points = chain.get_entry_points(v121_metadata)
    assert "mcp_server" in entry_points
    assert "hatch_mcp_server" in entry_points
```

## Related Documentation

- [Chain of Responsibility Pattern](../architecture/ChainOfResponsibilityPattern.md) - Core pattern implementation
- [Component Types](../architecture/ComponentTypes.md) - Understanding different component types
- [Schema Integration](../architecture/SchemaIntegration.md) - Schema management integration
