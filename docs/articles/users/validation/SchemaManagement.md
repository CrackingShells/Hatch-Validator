# Schema Management

This article is about:
- Automatic schema version detection and resolution
- Schema fetching and caching mechanisms through SchemaFetcher and SchemaCache
- Integration with Hatch-Schemas repository for schema updates
- Schema evolution handling without breaking consumer code

## Overview

Hatch-Validator's schema management system provides automatic schema fetching, caching, and version resolution. The system integrates with the external Hatch-Schemas repository to ensure validators always have access to the latest schema definitions while maintaining local caches for offline operation.

## Schema Management Components

### SchemaRetriever

The SchemaRetriever class serves as the main interface for schema operations, coordinating between fetching and caching:

```python
from hatch_validator.schemas.schemas_retriever import SchemaRetriever

# Initialize with default cache directory
retriever = SchemaRetriever()

# Get latest package schema
package_schema = retriever.get_schema("package", "latest")

# Get specific version
package_schema_v120 = retriever.get_schema("package", "v1.2.0")
```

### SchemaFetcher

The SchemaFetcher class handles network operations to retrieve schemas from the Hatch-Schemas GitHub repository:

**Key Features:**
- Discovers latest schema versions via GitHub API
- Downloads schemas directly from GitHub releases
- Handles network errors and timeouts gracefully

**Schema Types Supported:**
- **Package Schemas**: `hatch_pkg_metadata_schema.json` files
- **Registry Schemas**: `hatch_all_pkg_metadata_schema.json` files

### SchemaCache

The SchemaCache class manages local schema storage and retrieval:

**Key Features:**
- Caches schemas locally for offline use
- Manages schema versioning and updates
- Provides cache freshness validation
- Supports version-specific schema storage

**Cache Location:**
- Default: `~/.hatch/schemas/`
- Configurable through constructor parameter

## Automatic Schema Version Detection

### Version Resolution Process

The schema management system automatically resolves schema versions:

1. **Latest Version Discovery**: Query GitHub API for latest schema releases
2. **Version Mapping**: Map schema types to their latest available versions
3. **Cache Validation**: Check if cached schemas are fresh and up-to-date
4. **Automatic Updates**: Download new schemas when cache is stale or missing

### Schema Version Handling

```python
from hatch_validator.schemas.schemas_retriever import get_package_schema, get_registry_schema

# Get latest package schema (automatically resolves to newest version)
latest_package_schema = get_package_schema("latest")

# Get specific version
v121_package_schema = get_package_schema("v1.2.1")

# Force update check
fresh_schema = get_package_schema("latest", force_update=True)
```

## Integration with Hatch-Schemas Repository

### GitHub Integration

The schema management system integrates with the Hatch-Schemas repository:

**Repository Structure:**
- **Package Schemas**: Tagged with `schemas-package-` prefix (e.g., `schemas-package-v1.2.1`)
- **Registry Schemas**: Tagged with `schemas-registry-` prefix (e.g., `schemas-registry-v1.1.0`)

**API Endpoints:**
- **Releases API**: `https://api.github.com/repos/CrackingShells/Hatch-Schemas/releases`
- **Download URLs**: `https://github.com/CrackingShells/Hatch-Schemas/releases/download/{tag}/{filename}`

### Automatic Schema Discovery

The system automatically discovers available schema versions:

```python
from hatch_validator.schemas.schema_fetcher import SchemaFetcher

fetcher = SchemaFetcher()

# Get latest schema information from GitHub
schema_info = fetcher.get_latest_schema_info()

# Returns structure like:
# {
#     "latest_package_version": "v1.2.1",
#     "latest_registry_version": "v1.1.0",
#     "package": {
#         "version": "v1.2.1",
#         "url": "https://github.com/.../schemas-package-v1.2.1/hatch_pkg_metadata_schema.json"
#     },
#     "registry": {
#         "version": "v1.1.0", 
#         "url": "https://github.com/.../schemas-registry-v1.1.0/hatch_all_pkg_metadata_schema.json"
#     }
# }
```

## Schema Caching and Updates

### Cache Management

The schema cache provides efficient local storage:

**Cache Structure:**
```
~/.hatch/schemas/
├── schema_info.json              # Cache metadata and version info
├── hatch_pkg_metadata_schema.json    # Latest package schema
├── hatch_all_pkg_metadata_schema.json # Latest registry schema
└── v1.2.1/                       # Version-specific schemas
    ├── hatch_pkg_metadata_schema.json
    └── hatch_all_pkg_metadata_schema.json
```

### Cache Freshness

The system automatically manages cache freshness:

```python
from hatch_validator.schemas.schema_cache import SchemaCache

cache = SchemaCache()

# Check if cache is fresh (default: 24 hours)
is_fresh = cache.is_fresh()

# Check with custom TTL (12 hours)
is_fresh = cache.is_fresh(max_age=43200)
```

**Default Cache TTL**: 24 hours (86400 seconds)

### Automatic Updates

Schema updates happen automatically:

1. **Cache Check**: Verify cache freshness on schema requests
2. **Update Check**: Query GitHub for latest schema versions if cache is stale
3. **Download**: Fetch new schemas if newer versions are available
4. **Cache Update**: Store new schemas locally with version information

## Schema Evolution Handling

### Backward Compatibility

The schema management system ensures backward compatibility:

**Version-Specific Storage:**
- Schemas are stored both in version-specific directories and as latest versions
- Older schema versions remain accessible for legacy package validation
- Version resolution handles both `v1.2.1` and `1.2.1` format variations

**Graceful Degradation:**
- If latest schema is unavailable, system falls back to cached versions
- Network failures don't prevent validation with cached schemas
- Missing schemas trigger automatic download attempts

### Schema Version Migration

When new schema versions are released:

1. **Automatic Discovery**: System detects new schema versions from GitHub
2. **Incremental Download**: Only new or updated schemas are downloaded
3. **Version Coexistence**: Multiple schema versions can coexist in cache
4. **Transparent Updates**: Consumer code continues working without changes

## Error Handling and Resilience

### Network Error Handling

The schema management system handles network issues gracefully:

```python
# Network errors are logged but don't prevent operation
try:
    schema = get_package_schema("latest", force_update=True)
except Exception as e:
    # Falls back to cached schema if available
    schema = get_package_schema("latest", force_update=False)
```

### Cache Corruption Recovery

The system recovers from cache corruption:

- **Validation**: JSON parsing errors trigger cache invalidation
- **Redownload**: Corrupted schemas are automatically redownloaded
- **Fallback**: System attempts multiple schema sources before failing

### Offline Operation

Schema management supports offline operation:

- **Local Cache**: Schemas are cached locally for offline use
- **Graceful Degradation**: Network unavailability doesn't prevent validation
- **Cache Persistence**: Schemas remain available across application restarts

## Configuration and Customization

### Custom Cache Directory

```python
from pathlib import Path
from hatch_validator.schemas.schemas_retriever import SchemaRetriever

# Use custom cache directory
custom_cache = Path("/custom/cache/path")
retriever = SchemaRetriever(cache_dir=custom_cache)
```

### Force Updates

```python
# Force schema update regardless of cache freshness
schema = get_package_schema("latest", force_update=True)

# Force update for specific version
schema = get_package_schema("v1.2.1", force_update=True)
```

### Cache TTL Configuration

```python
from hatch_validator.schemas.schema_cache import SchemaCache

# Custom cache TTL (6 hours)
cache = SchemaCache()
is_fresh = cache.is_fresh(max_age=21600)
```

## Integration with Validation System

### Automatic Schema Loading

The validation system automatically loads appropriate schemas:

```python
from hatch_validator import HatchPackageValidator

# Validator automatically loads latest schemas
validator = HatchPackageValidator(
    version="latest",
    force_schema_update=True  # Force schema cache update
)
```

### Schema Version Coordination

The schema management system coordinates with the Chain of Responsibility validation:

1. **Schema Detection**: Validator detects package schema version from metadata
2. **Schema Loading**: Appropriate schema is loaded from cache or downloaded
3. **Validation**: Package is validated against the correct schema version
4. **Chain Delegation**: Validation delegates through version-appropriate validators

## Performance Considerations

### Efficient Caching

- **Lazy Loading**: Schemas are loaded only when needed
- **Version Caching**: Multiple schema versions cached simultaneously
- **Network Optimization**: Only updated schemas are downloaded

### Background Updates

- **Asynchronous Updates**: Schema updates can happen in background
- **Cache Warming**: Schemas can be pre-loaded for better performance
- **Batch Operations**: Multiple schemas updated in single network operation

## Related Documentation

- [Package Validation Guide](PackageValidation.md) - How validation uses schema management
- [Chain of Responsibility Pattern](../../devs/architecture/ChainOfResponsibilityPattern.md) - Validation architecture
- [Schema Integration](../../devs/architecture/SchemaIntegration.md) - Technical integration details
