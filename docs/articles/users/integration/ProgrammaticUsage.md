# Programmatic Usage

This article is about:

- Real-world integration patterns from first-party consumers
- Dependency Installation Orchestrator usage of PackageService and RegistryService
- Environment Manager integration with RegistryService and HatchPackageValidator
- CLI integration patterns and validation workflows
- Best practices derived from actual production implementations

## Overview

This guide provides comprehensive examples of how Hatch-Validator is integrated in production environments. All examples are derived from actual first-party consumer implementations, demonstrating the practical benefits of version-agnostic data access and the Chain of Responsibility architecture.

## Dependency Installation Orchestrator Integration

### PackageService Usage Patterns

The Dependency Installation Orchestrator uses PackageService to access package metadata without schema version awareness:

```python
from hatch_validator.package.package_service import PackageService

class DependencyInstallerOrchestrator:
    def _resolve_package_location(self, package_path_or_name: str, 
                                  version_constraint: Optional[str] = None,
                                  force_download: bool = False) -> Tuple[Path, Dict[str, Any]]:
        """Resolve package location and load metadata using PackageService."""
        
        if Path(package_path_or_name).exists():
            # Local package - load metadata directly
            metadata_path = Path(package_path_or_name) / "hatch_metadata.json"
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # PackageService automatically handles schema version detection
            self.package_service = PackageService(metadata)
            return Path(package_path_or_name), metadata
        
        else:
            # Remote package - resolve through registry
            compatible_version = self.registry_service.find_compatible_version(
                package_path_or_name, version_constraint)
            
            location = self.registry_service.get_package_uri(
                package_path_or_name, compatible_version)
            
            downloaded_path = self.package_loader.download_package(
                location, package_path_or_name, compatible_version, 
                force_download=force_download)
            
            # Load metadata and initialize PackageService
            metadata_path = downloaded_path / "hatch_metadata.json"
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Version-agnostic metadata access
            self.package_service = PackageService(metadata)
            return downloaded_path, metadata
```

### Version-Agnostic Dependency Access

The orchestrator accesses dependencies without knowing the schema version:

```python
def _build_dependency_graph(self, package_path: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Build dependency graph using version-agnostic PackageService."""
    
    # PackageService abstracts schema version differences
    all_deps = self.package_service.get_dependencies()
    
    # Process dependencies by type - works with any schema version
    install_plan = {
        "dependencies_to_install": {},
        "main_package": {
            "path": package_path,
            "metadata": metadata
        }
    }
    
    # Handle all dependency types uniformly
    for dep_type, dependencies in all_deps.items():
        if dependencies:
            install_plan["dependencies_to_install"][dep_type] = dependencies
            self.logger.info(f"Found {len(dependencies)} {dep_type} dependencies")
    
    return install_plan
```

**Key Benefits:**

- **Schema Transparency**: Orchestrator doesn't need to know about v1.1.0 vs v1.2.0 vs v1.2.1 differences
- **Unified Processing**: Same code handles separate dependencies (v1.1.0) and unified dependencies (v1.2.0+)
- **Future Compatibility**: New schema versions work without orchestrator changes

### RegistryService Integration

The orchestrator uses RegistryService for version-agnostic registry operations:

```python
def install_dependencies(self, package_path_or_name: str, env_path: Path, 
                        env_name: str, existing_packages: Dict[str, str],
                        version_constraint: Optional[str] = None,
                        force_download: bool = False, 
                        auto_approve: bool = False) -> Tuple[bool, List[Dict[str, Any]]]:
    """Install dependencies using version-agnostic registry operations."""
    
    try:
        # Step 1: Resolve package location using RegistryService
        package_path, metadata = self._resolve_package_location(
            package_path_or_name, version_constraint, force_download)
        
        # Step 2: Check package existence without schema awareness
        if not Path(package_path_or_name).exists():
            if not self.registry_service.package_exists(package_path_or_name):
                raise DependencyInstallationError(
                    f"Package {package_path_or_name} does not exist in registry")
        
        # Step 3: Build dependency graph using PackageService
        install_plan = self._build_dependency_graph(package_path, metadata)
        
        # Step 4: Execute installation plan
        installed_packages = self._execute_install_plan(install_plan, env_path, env_name)
        
        return True, installed_packages
        
    except Exception as e:
        self.logger.error(f"Dependency installation failed: {e}")
        raise DependencyInstallationError(f"Installation failed: {e}") from e
```

## Environment Manager Integration

### RegistryService Initialization

The Environment Manager initializes RegistryService for version-agnostic registry access:

```python
from hatch_validator.registry.registry_service import RegistryService

class HatchEnvironmentManager:
    def __init__(self, cache_dir: Path = None, cache_ttl: int = 3600, 
                 simulation_mode: bool = False, 
                 local_registry_cache_path: Optional[Path] = None):
        """Initialize environment manager with registry service."""
        
        # Initialize registry retriever and get registry data
        self.retriever = RegistryRetriever(
            cache_ttl=cache_ttl,
            local_cache_dir=cache_dir,
            simulation_mode=simulation_mode,
            local_registry_cache_path=local_registry_cache_path
        )
        self.registry_data = self.retriever.get_registry()
        
        # Initialize RegistryService with automatic schema detection
        self.registry_service = RegistryService(self.registry_data)
        
        # Initialize dependency orchestrator with registry service
        self.dependency_orchestrator = DependencyInstallerOrchestrator(
            package_loader=self.package_loader,
            registry_service=self.registry_service,
            registry_data=self.registry_data
        )
```

### Registry Data Refresh

The environment manager handles registry updates transparently:

```python
def refresh_registry_data(self, force_refresh: bool = False) -> None:
    """Refresh registry data and update services."""
    
    self.logger.info("Refreshing registry data...")
    try:
        # Get updated registry data
        self.registry_data = self.retriever.get_registry(force_refresh=force_refresh)
        
        # Update RegistryService with new data - automatic schema detection
        self.registry_service = RegistryService(self.registry_data)
        
        # Update orchestrator with new registry service
        self.dependency_orchestrator.registry_service = self.registry_service
        self.dependency_orchestrator.registry_data = self.registry_data
        
        self.logger.info("Registry data refreshed successfully")
    except Exception as e:
        self.logger.error(f"Failed to refresh registry data: {e}")
        raise
```

### Package Installation Integration

The environment manager uses the dependency orchestrator for package installation:

```python
def install_package(self, package_path_or_name: str, env_name: str, 
                   version_constraint: Optional[str] = None,
                   force_download: bool = False, 
                   auto_approve: bool = False) -> bool:
    """Install package using version-agnostic services."""
    
    try:
        env_path = self.get_environment_path(env_name)
        existing_packages = self.get_installed_packages(env_name)
        
        # Use dependency orchestrator with version-agnostic services
        success, installed_packages = self.dependency_orchestrator.install_dependencies(
            package_path_or_name=package_path_or_name,
            env_path=env_path,
            env_name=env_name,
            existing_packages=existing_packages,
            version_constraint=version_constraint,
            force_download=force_download,
            auto_approve=auto_approve
        )
        
        if success:
            self._save_environments()
            self.logger.info(f"Successfully installed package in environment {env_name}")
        
        return success
        
    except Exception as e:
        self.logger.error(f"Package installation failed: {e}")
        return False
```

## CLI Integration Patterns

### HatchPackageValidator Usage

The CLI uses HatchPackageValidator for comprehensive package validation:

```python
from hatch_validator import HatchPackageValidator

def main():
    """Main CLI entry point with validation integration."""
    
    # Initialize environment manager for registry data
    env_manager = HatchEnvironmentManager()
    
    # Parse command line arguments
    args = parse_arguments()
    
    if args.command == "validate":
        package_path = Path(args.package_dir).resolve()
        
        # Create validator with registry data from environment manager
        validator = HatchPackageValidator(
            version="latest",
            allow_local_dependencies=True,
            registry_data=env_manager.registry_data  # Version-agnostic registry data
        )
        
        # Validate package - automatic schema version detection
        is_valid, validation_results = validator.validate_package(package_path)
        
        if is_valid:
            print(f"Package validation SUCCESSFUL: {package_path}")
            return 0
        else:
            print(f"Package validation FAILED: {package_path}")
            
            # Print detailed validation results
            if validation_results and isinstance(validation_results, dict):
                for category, result in validation_results.items():
                    if category not in ['valid', 'metadata'] and isinstance(result, dict):
                        if not result.get('valid', True) and result.get('errors'):
                            print(f"\n{category.replace('_', ' ').title()} errors:")
                            for error in result['errors']:
                                print(f"  - {error}")
            
            return 1
```

### Validation Error Handling

The CLI implements comprehensive error handling for validation results:

```python
def handle_validation_results(validation_results: Dict[str, Any]) -> int:
    """Handle and display validation results."""
    
    if validation_results.get('valid', False):
        print("✓ Package validation successful")
        return 0
    
    print("✗ Package validation failed")
    
    # Handle schema validation errors
    if not validation_results.get('metadata_schema', {}).get('valid', True):
        print("\nSchema Validation Errors:")
        for error in validation_results['metadata_schema'].get('errors', []):
            print(f"  - {error}")
    
    # Handle entry point validation errors
    if not validation_results.get('entry_point', {}).get('valid', True):
        print("\nEntry Point Validation Errors:")
        for error in validation_results['entry_point'].get('errors', []):
            print(f"  - {error}")
    
    # Handle dependency validation errors
    if not validation_results.get('dependencies', {}).get('valid', True):
        print("\nDependency Validation Errors:")
        for error in validation_results['dependencies'].get('errors', []):
            print(f"  - {error}")
    
    # Handle tools validation errors
    if not validation_results.get('tools', {}).get('valid', True):
        print("\nTools Validation Errors:")
        for error in validation_results['tools'].get('errors', []):
            print(f"  - {error}")
    
    return 1
```

## Best Practices from Production Usage

### Service Initialization Patterns

**Centralized Service Management:**

```python
class ServiceManager:
    """Centralized management of Hatch-Validator services."""
    
    def __init__(self, registry_data: Dict[str, Any]):
        self.registry_service = RegistryService(registry_data)
        self.package_service = None  # Initialized per package
        
    def load_package(self, metadata: Dict[str, Any]) -> PackageService:
        """Load package with version-agnostic service."""
        self.package_service = PackageService(metadata)
        return self.package_service
    
    def validate_package(self, package_path: Path) -> Tuple[bool, Dict[str, Any]]:
        """Validate package using integrated services."""
        validator = HatchPackageValidator(
            version="latest",
            allow_local_dependencies=True,
            registry_data=self.registry_service._registry_data
        )
        return validator.validate_package(package_path)
```

### Error Handling Patterns

**Graceful Degradation:**

```python
def safe_package_operation(package_path: Path, registry_data: Dict[str, Any]) -> bool:
    """Perform package operations with graceful error handling."""
    
    try:
        # Primary operation with full services
        service = PackageService()
        with open(package_path / "hatch_metadata.json", 'r') as f:
            metadata = json.load(f)
        
        service.load_metadata(metadata)
        dependencies = service.get_dependencies()
        return True
        
    except ValueError as e:
        # Handle schema version issues
        logger.warning(f"Schema version issue: {e}")
        return False
        
    except Exception as e:
        # Handle other errors gracefully
        logger.error(f"Package operation failed: {e}")
        return False
```

### Performance Optimization Patterns

**Service Reuse:**

```python
class OptimizedPackageProcessor:
    """Optimized package processing with service reuse."""
    
    def __init__(self, registry_data: Dict[str, Any]):
        # Initialize registry service once
        self.registry_service = RegistryService(registry_data)
        
        # Initialize validator once
        self.validator = HatchPackageValidator(
            version="latest",
            allow_local_dependencies=True,
            registry_data=registry_data
        )
    
    def process_packages(self, package_paths: List[Path]) -> List[Dict[str, Any]]:
        """Process multiple packages efficiently."""
        results = []
        
        for package_path in package_paths:
            # Reuse validator instance
            is_valid, validation_results = self.validator.validate_package(package_path)
            
            # Create new PackageService per package
            with open(package_path / "hatch_metadata.json", 'r') as f:
                metadata = json.load(f)
            
            package_service = PackageService(metadata)
            dependencies = package_service.get_dependencies()
            
            results.append({
                'path': package_path,
                'valid': is_valid,
                'dependencies': dependencies,
                'validation_results': validation_results
            })
        
        return results
```

## Integration Benefits Demonstrated

### Schema Version Transparency

All production integrations demonstrate that consumer code remains stable across schema versions:

- **Dependency Orchestrator**: Same code processes v1.1.0 (separate dependencies) and v1.2.0+ (unified dependencies)
- **Environment Manager**: Registry operations work regardless of registry schema version
- **CLI Validation**: Validation commands work with any package schema version

### Reduced Complexity

Production code focuses on business logic rather than schema management:

- **No Version Checks**: No conditional logic based on schema versions
- **Consistent APIs**: Same method signatures across all integrations
- **Unified Error Handling**: Consistent error patterns across schema versions

### Future Compatibility

All integrations automatically support new schema versions:

- **Automatic Discovery**: New schema versions are detected and handled automatically
- **Delegation Benefits**: New functionality is added without breaking existing code
- **Zero Migration**: No code changes required when new schema versions are released

## Related Documentation

- [PackageService Guide](../data_access/PackageService.md) - Detailed PackageService API
- [RegistryService Guide](../data_access/RegistryService.md) - Detailed RegistryService API
- [Version-Agnostic Access Concepts](../data_access/VersionAgnosticAccess.md) - Core principles
- [Chain of Responsibility Pattern](../../devs/architecture/ChainOfResponsibilityPattern.md) - Architectural foundation
