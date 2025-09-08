# Schema Integration

This article is about:
- Integration with Hatch-Schemas repository for schema management
- Schema fetching, caching, and version resolution mechanisms
- How schema evolution is handled across all component types
- Version detection and automatic chain selection processes

## Overview

Hatch-Validator integrates with the external Hatch-Schemas repository to provide automatic schema management, version detection, and chain selection. This integration ensures that validators always have access to the latest schema definitions while maintaining backward compatibility and offline operation capabilities.

## Hatch-Schemas Repository Integration

### Repository Structure

The Hatch-Schemas repository provides versioned schema definitions:

**GitHub Repository**: `CrackingShells/Hatch-Schemas`

**Schema Types:**
- **Package Schemas**: `hatch_pkg_metadata_schema.json` - Define package metadata structure
- **Registry Schemas**: `hatch_all_pkg_metadata_schema.json` - Define registry data structure

**Release Tagging:**
- **Package Schema Releases**: Tagged with `schemas-package-` prefix (e.g., `schemas-package-v1.2.1`)
- **Registry Schema Releases**: Tagged with `schemas-registry-` prefix (e.g., `schemas-registry-v1.1.0`)

### API Integration

The schema management system integrates with GitHub APIs:

**GitHub Releases API:**
```
https://api.github.com/repos/CrackingShells/Hatch-Schemas/releases
```

**Schema Download URLs:**
```
https://github.com/CrackingShells/Hatch-Schemas/releases/download/{tag}/{filename}
```

**Example Integration:**
```python
from hatch_validator.schemas.schema_fetcher import SchemaFetcher

fetcher = SchemaFetcher()

# Discover latest schema versions
schema_info = fetcher.get_latest_schema_info()
# Returns:
# {
#     "latest_package_version": "v1.2.1",
#     "latest_registry_version": "v1.1.0",
#     "package": {
#         "version": "v1.2.1",
#         "url": "https://github.com/.../schemas-package-v1.2.1/hatch_pkg_metadata_schema.json"
#     }
# }

# Download specific schema
schema_data = fetcher.download_schema(schema_info['package']['url'])
```

## Schema Fetching and Caching

### SchemaFetcher Integration

The SchemaFetcher class handles network operations with the Hatch-Schemas repository:

**Key Methods:**
- `get_latest_schema_info()`: Discovers latest schema versions via GitHub API
- `download_schema(url)`: Downloads schema JSON files from GitHub releases

**Network Resilience:**
```python
def download_schema(self, url: str) -> Optional[Dict[str, Any]]:
    """Download schema with error handling."""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, json.JSONDecodeError) as e:
        logger.error(f"Error downloading schema: {e}")
        return None  # Graceful degradation to cached schemas
```

### SchemaCache Integration

The SchemaCache class manages local schema storage:

**Cache Structure:**
```
~/.hatch/schemas/
├── schema_info.json                      # Cache metadata
├── hatch_pkg_metadata_schema.json        # Latest package schema
├── hatch_all_pkg_metadata_schema.json    # Latest registry schema
└── v1.2.1/                              # Version-specific storage
    ├── hatch_pkg_metadata_schema.json
    └── hatch_all_pkg_metadata_schema.json
```

**Cache Management:**
```python
from hatch_validator.schemas.schema_cache import SchemaCache

cache = SchemaCache()

# Check cache freshness (default: 24 hours)
if not cache.is_fresh():
    # Cache is stale, trigger update
    schema_retriever.update_schemas()

# Load cached schema
schema = cache.load_schema("package", "v1.2.1")
```

### SchemaRetriever Coordination

The SchemaRetriever class coordinates fetching and caching:

```python
from hatch_validator.schemas.schemas_retriever import SchemaRetriever

retriever = SchemaRetriever()

# Get schema with automatic cache management
schema = retriever.get_schema("package", "latest", force_update=False)

# Process:
# 1. Check cache freshness
# 2. If stale, fetch latest schema info from GitHub
# 3. Download new schemas if available
# 4. Update cache with new schemas
# 5. Return requested schema
```

## Schema Evolution Handling

### Version Detection

The system automatically detects schema versions from metadata:

```python
def detect_schema_version(metadata: Dict[str, Any]) -> str:
    """Detect schema version from package metadata."""
    schema_version = metadata.get("package_schema_version")
    
    if not schema_version:
        # Fallback to default version for legacy packages
        return "1.1.0"
    
    # Normalize version format (remove 'v' prefix if present)
    return schema_version.lstrip('v')
```

### Automatic Chain Selection

Schema version detection drives automatic chain selection:

```python
class ValidatorFactory:
    @classmethod
    def create_validator_chain(cls, target_version: Optional[str] = None) -> Validator:
        """Create validator chain based on detected schema version."""
        
        if target_version is None:
            # Use latest available version
            target_version = cls._version_order[0]
        
        # Normalize version format
        target_version = target_version.lstrip('v')
        
        # Create chain from target version to oldest
        target_index = cls._version_order.index(target_version)
        chain_versions = cls._version_order[target_index:]
        
        # Build and link chain
        validators = [cls._validator_registry[v]() for v in chain_versions]
        for i in range(len(validators) - 1):
            validators[i].set_next(validators[i + 1])
        
        return validators[0]
```

### Schema Compatibility

The system handles schema compatibility across versions:

**Forward Compatibility:**
- Newer validators can handle older schema versions through delegation
- Chain construction ensures appropriate validator is selected

**Backward Compatibility:**
- Older schema versions continue to work with newer validator implementations
- Terminal validators (v1.1.0) provide complete baseline functionality

**Example Compatibility Matrix:**
```
Schema Version | Validator Chain
v1.1.0        | v1.1.0 (terminal)
v1.2.0        | v1.2.0 → v1.1.0
v1.2.1        | v1.2.1 → v1.2.0 → v1.1.0
```

## Integration with Component Types

### Validator Integration

Validators use schema information for validation:

```python
class SchemaValidation:
    def validate(self, metadata: Dict, context: ValidationContext) -> Tuple[bool, List[str]]:
        """Validate metadata against appropriate schema."""
        
        schema_version = metadata.get("package_schema_version", "1.1.0")
        
        # Get appropriate schema from cache/repository
        schema = get_package_schema(schema_version)
        if not schema:
            return False, [f"Schema not available for version {schema_version}"]
        
        # Validate metadata against schema
        try:
            jsonschema.validate(metadata, schema)
            return True, []
        except jsonschema.ValidationError as e:
            return False, [f"Schema validation error: {e.message}"]
```

### Package Accessor Integration

Package accessors adapt to schema structure changes:

```python
class V120PackageAccessor(HatchPkgAccessorBase):
    def get_dependencies(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Access dependencies based on v1.2.0 schema structure."""
        
        # v1.2.0 introduced unified dependencies structure
        dependencies = metadata.get('dependencies', {})
        
        # Validate structure matches expected schema
        expected_types = ['hatch', 'python', 'system', 'docker']
        for dep_type in dependencies:
            if dep_type not in expected_types:
                logger.warning(f"Unexpected dependency type: {dep_type}")
        
        return dependencies
```

### Registry Accessor Integration

Registry accessors handle registry schema evolution:

```python
class V110RegistryAccessor(RegistryAccessorBase):
    def can_handle(self, registry_data: Dict[str, Any]) -> bool:
        """Check if this accessor can handle the registry schema."""
        
        # Check for v1.1.0 registry schema indicators
        schema_version = registry_data.get('registry_schema_version', '')
        if schema_version.startswith('1.1.'):
            return True
        
        # Check for CrackingShells registry structure
        if 'repositories' in registry_data:
            return True
        
        return False
```

## Automatic Schema Updates

### Update Triggers

Schema updates are triggered by several events:

**Time-Based Updates:**
- Cache TTL expiration (default: 24 hours)
- Forced update requests (`force_update=True`)

**Event-Based Updates:**
- Application startup with stale cache
- Schema loading failures
- Validation errors due to missing schemas

### Update Process

The schema update process is coordinated across components:

```python
def update_schemas() -> bool:
    """Coordinate schema updates across the system."""
    
    # 1. Fetch latest schema information from GitHub
    fetcher = SchemaFetcher()
    latest_info = fetcher.get_latest_schema_info()
    
    if not latest_info:
        logger.warning("Failed to fetch latest schema info")
        return False
    
    # 2. Check for new schema versions
    cache = SchemaCache()
    current_info = cache.get_info()
    
    updated = False
    for schema_type in ['package', 'registry']:
        current_version = current_info.get(f"latest_{schema_type}_version")
        latest_version = latest_info.get(f"latest_{schema_type}_version")
        
        if current_version != latest_version:
            # 3. Download new schema
            schema_url = latest_info[schema_type]['url']
            schema_data = fetcher.download_schema(schema_url)
            
            if schema_data:
                # 4. Update cache
                cache.save_schema(schema_type, schema_data, latest_version)
                cache.save_schema(schema_type, schema_data)  # Also save as latest
                updated = True
                logger.info(f"Updated {schema_type} schema to {latest_version}")
    
    # 5. Update cache metadata
    if updated:
        cache.update_info(latest_info)
    
    return updated
```

### Component Coordination

Schema updates coordinate with component factories:

```python
class ValidatorFactory:
    @classmethod
    def _ensure_validators_loaded(cls) -> None:
        """Ensure validators are loaded and schemas are current."""
        
        # Check for schema updates before loading validators
        schema_retriever.get_schema("package", "latest")  # Triggers update check
        
        # Load validators based on available schemas
        if not cls._validator_registry:
            # Auto-discover and register validators
            cls._discover_validators()
```

## Error Handling and Resilience

### Network Failure Handling

The system gracefully handles network failures:

```python
def get_schema_with_fallback(schema_type: str, version: str) -> Optional[Dict[str, Any]]:
    """Get schema with network failure fallback."""
    
    try:
        # Try to get latest schema (may trigger network request)
        return schema_retriever.get_schema(schema_type, version, force_update=True)
    except requests.RequestException:
        # Network failure - fall back to cached schema
        logger.warning("Network failure, using cached schema")
        return schema_retriever.get_schema(schema_type, version, force_update=False)
    except Exception as e:
        # Other errors - log and continue with cached schema
        logger.error(f"Schema retrieval error: {e}")
        return schema_retriever.get_schema(schema_type, version, force_update=False)
```

### Schema Validation Errors

The system handles schema validation errors gracefully:

```python
def validate_with_fallback(metadata: Dict, schema_version: str) -> Tuple[bool, List[str]]:
    """Validate with schema fallback."""
    
    # Try validation with specific schema version
    schema = get_package_schema(schema_version)
    if schema:
        try:
            jsonschema.validate(metadata, schema)
            return True, []
        except jsonschema.ValidationError as e:
            return False, [f"Schema validation error: {e.message}"]
    
    # Fallback to latest schema if specific version unavailable
    latest_schema = get_package_schema("latest")
    if latest_schema:
        try:
            jsonschema.validate(metadata, latest_schema)
            logger.warning(f"Validated with latest schema instead of {schema_version}")
            return True, []
        except jsonschema.ValidationError as e:
            return False, [f"Schema validation error (latest): {e.message}"]
    
    # No schema available - skip schema validation
    logger.error("No schema available for validation")
    return True, ["Schema validation skipped - no schema available"]
```

### Cache Corruption Recovery

The system recovers from cache corruption:

```python
def load_schema_with_recovery(schema_type: str, version: str) -> Optional[Dict[str, Any]]:
    """Load schema with corruption recovery."""
    
    try:
        return cache.load_schema(schema_type, version)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"Cache corruption detected: {e}")
        
        # Remove corrupted cache file
        cache_path = cache.get_schema_path(schema_type, version)
        if cache_path.exists():
            cache_path.unlink()
        
        # Trigger fresh download
        return schema_retriever.get_schema(schema_type, version, force_update=True)
```

## Performance Optimization

### Lazy Schema Loading

Schemas are loaded only when needed:

```python
class LazySchemaLoader:
    def __init__(self):
        self._schema_cache = {}
    
    def get_schema(self, schema_type: str, version: str) -> Optional[Dict[str, Any]]:
        """Get schema with lazy loading."""
        
        cache_key = f"{schema_type}:{version}"
        
        if cache_key not in self._schema_cache:
            # Load schema on first access
            self._schema_cache[cache_key] = schema_retriever.get_schema(schema_type, version)
        
        return self._schema_cache[cache_key]
```

### Background Updates

Schema updates can happen in the background:

```python
import threading

def background_schema_update():
    """Update schemas in background thread."""
    
    def update_worker():
        try:
            schema_retriever.get_schema("package", "latest", force_update=True)
            schema_retriever.get_schema("registry", "latest", force_update=True)
            logger.info("Background schema update completed")
        except Exception as e:
            logger.error(f"Background schema update failed: {e}")
    
    # Start background update
    update_thread = threading.Thread(target=update_worker, daemon=True)
    update_thread.start()
```

## Related Documentation

- [Chain of Responsibility Pattern](ChainOfResponsibilityPattern.md) - Core architectural pattern
- [Component Types](ComponentTypes.md) - How components use schema information
- [Schema Management](../../users/validation/SchemaManagement.md) - User-facing schema management
