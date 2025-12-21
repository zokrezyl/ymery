# Ymery Plugin System

Ymery uses a plugin architecture to extend functionality. Plugins are organized by category and loaded dynamically at runtime.

## Plugin Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     PluginManager                           │
│  - Scans plugins/ directory for main.py files               │
│  - Loads and registers plugins using decorators             │
│  - Implements TreeLike interface for browsing               │
└─────────────────────────────────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │  Frontend   │ │   Backend   │ │   Other     │
    │  Plugins    │ │   Plugins   │ │   Plugins   │
    │  (Widgets)  │ │ (TreeLike)  │ │             │
    └─────────────┘ └─────────────┘ └─────────────┘
```

## Plugin Categories

### Backend Plugins (TreeLike Implementations)

Backend plugins implement the `TreeLike` interface to provide hierarchical data access:

| Plugin | Description | Key Features |
|--------|-------------|--------------|
| `data-tree` | In-memory hierarchical data | Read/write, YAML-defined structure |
| `simple-data-tree` | Wrapper for Python data | Maps dict/list/primitives to TreeLike |
| `log-tree` | Application logging | Read-only log entries |
| `kernel` | External data sources | Aggregates device managers |
| `filesystem` | File system browsing | Audio file discovery and opening |
| `waveform-st` | Waveform generation | Single-threaded for Pyodide |
| `soundfile` | Audio file access | Read audio files via soundfile library |

### Frontend Plugins (Widgets)

Frontend plugins provide UI components. See `ymery-lang.md` for widget documentation.

## TreeLike Interface

All backend plugins implement the `TreeLike` abstract interface:

```python
class TreeLike(ABC):
    """Hierarchical data access interface"""

    @abstractmethod
    def get_children_names(self, path: DataPath) -> Result[List[str]]:
        """Get child node names at path"""
        pass

    @abstractmethod
    def get_metadata(self, path: DataPath) -> Result[Dict]:
        """Get metadata dictionary for node at path"""
        pass

    @abstractmethod
    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        """Get list of metadata keys at path"""
        pass

    @abstractmethod
    def get(self, path: DataPath) -> Result[Any]:
        """Get metadata value (path ends with key name)"""
        pass

    @abstractmethod
    def set(self, path: DataPath, value: Any) -> Result[None]:
        """Set metadata value at path"""
        pass

    @abstractmethod
    def add_child(self, path: DataPath, name: str, data: Any) -> Result[None]:
        """Add child node to parent at path"""
        pass
```

### Path Convention

- All paths are `DataPath` instances
- Paths are absolute within the plugin namespace (start with `/`)
- Last component of `get()` path is the metadata key
- Example: `get(DataPath("/user/name/label"))` returns the `label` value for `/user/name`

## Creating a Backend Plugin

### 1. Directory Structure

```
src/ymery/plugins/
└── my_plugin/
    └── main.py
```

### 2. Plugin Implementation

```python
# src/ymery/plugins/my_plugin/main.py
from ymery.backend.types import DeviceManager, TreeLikeCache
from ymery.types import DataPath
from ymery.result import Result, Ok
from ymery.decorators import device_manager

@device_manager  # Register with PluginManager
class MyPluginManager(TreeLikeCache, DeviceManager):
    """Custom plugin that provides TreeLike access to some data"""

    def __init__(self):
        TreeLikeCache.__init__(self)  # Provides caching
        DeviceManager.__init__(self)
        self._data = {}

    def init(self) -> Result[None]:
        """Initialize plugin resources"""
        return Ok(None)

    def dispose(self) -> Result[None]:
        """Clean up plugin resources"""
        return Ok(None)

    def get_children_names_uncached(self, path: DataPath) -> Result[List[str]]:
        """Return child names (TreeLikeCache calls this when not cached)"""
        if len(path) == 0:
            return Ok(["available", "opened"])
        # ... handle subpaths
        return Ok([])

    def get_metadata_uncached(self, path: DataPath) -> Result[Dict]:
        """Return metadata dict (TreeLikeCache calls this when not cached)"""
        if len(path) == 0:
            return Ok({
                "name": "my-plugin",  # Required: unique plugin name
                "label": "My Plugin",
                "type": "my-plugin-manager",
                "category": "device-manager"
            })
        # ... handle subpaths
        return Result.error(f"Unknown path: {path}")

    def open(self, path: DataPath, params: Dict) -> Result:
        """Open a resource at path"""
        return Result.error("open: not implemented")

    def configure(self, path: DataPath, params: Dict) -> Result[None]:
        """Configure an opened resource"""
        return Result.error("configure: not implemented")

    def close(self, path: DataPath) -> Result[None]:
        """Close an opened resource"""
        return Result.error("close: not implemented")
```

### 3. Key Points

- Use `@device_manager` decorator for automatic registration
- Root metadata must include `name` field (unique plugin identifier)
- Extend `TreeLikeCache` for automatic caching with TTL
- Standard branches: `/available` (browseable resources), `/opened` (active resources)

## Standard Metadata Fields

Common metadata fields used across plugins:

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Unique identifier (required for root) |
| `label` | str | Display name |
| `type` | str | Node type (e.g., "folder", "audio-file", "audio-channel") |
| `category` | str | Category for filtering |
| `description` | str | Human-readable description |
| `capabilities` | dict | What operations are supported |
| `details` | dict | Type-specific details |
| `config-schema` | dict | Configuration parameters schema |

### Capabilities Object

```python
"capabilities": {
    "openable": True,   # Can be opened
    "configurable": True,  # Supports reconfiguration
    "closeable": True,  # Can be closed
    "readable": True,   # Provides data
    "writable": False   # Accepts data
}
```

## TreeLike Plugin Examples

### SimpleDataTree

Wraps any Python data structure (dict, list, primitives) as TreeLike:

```python
from ymery.plugins.backend.simple_data_tree.main import SimpleDataTree

# Wrap a Python dict
data = {"name": "Alice", "age": 30, "items": ["a", "b", "c"]}
tree = SimpleDataTree(data)

# Access as TreeLike
tree.get_children_names(DataPath("/"))     # ["name", "age", "items"]
tree.get_metadata(DataPath("/name"))       # {"label": "name: Alice"}
tree.get_children_names(DataPath("/items")) # ["0", "1", "2"]
```

### LogTree

Provides read-only access to application log entries:

```yaml
# In data.yaml
data:
  log-tree:
    type: log-tree

# In layout
- data-path: $log-tree
  builtin.tree-view:
```

### FilesystemManager

Browse and open audio files from the filesystem:

```python
# Structure:
# /available/fs-root/...  - browse from /
# /available/home/...     - browse from $HOME
# /available/mounts/...   - mounted filesystems
# /opened/0/...           - opened devices

# Open an audio file
manager.open(DataPath("/available/home/music/song.wav/0"), {})
```

### WaveformManagerST

Generate waveforms (single-threaded for Pyodide):

```python
# Available waveforms
# /available/sine/0
# /available/square/0
# /available/triangle/0

# Open a sine wave generator
manager.open(
    DataPath("/available/sine/0"),
    {"frequency": 440.0, "sample_rate": 48000}
)
```

## Using Plugins in YAML

### Referencing Plugin Data

```yaml
data:
  my-data:
    type: data-tree
    arg:
      children:
        kernel: $kernel          # Reference to kernel plugin

  log-tree:
    type: log-tree              # Use log-tree plugin
```

### In Widget Layouts

```yaml
widgets:
  my-widget:
    type: composite
    body:
      # Browse kernel data
      - data-path: kernel
        builtin.tree-view:

      # Show logs
      - data-path: $log-tree
        builtin.tree-view:
```

## Plugin Loading Process

1. `PluginManager` scans `src/ymery/plugins/` directory
2. For each subdirectory with `main.py`, it:
   - Loads the module dynamically
   - Collects classes decorated with `@device_manager`
3. For each registered class:
   - Creates instance via `create()` (calls `__init__` then `init()`)
   - Retrieves root metadata to get plugin `name`
   - Adds to internal tree under that name

## Best Practices

1. **Use TreeLikeCache**: Extend `TreeLikeCache` for automatic caching
2. **Return Results**: Always return `Result` objects, never raise exceptions
3. **Standard Branches**: Use `/available` and `/opened` pattern for resources
4. **Metadata Keys**: Include `name`, `label`, `type`, `category` at minimum
5. **Lazy Loading**: Don't load heavy resources until `open()` is called
6. **Proper Cleanup**: Implement `dispose()` to release resources

## Error Handling

All TreeLike methods return `Result` objects:

```python
from ymery.result import Result, Ok

def get_metadata(self, path: DataPath) -> Result[Dict]:
    if not self._is_valid(path):
        return Result.error(f"Invalid path: {path}")

    # Chain errors with context
    res = self._fetch_data(path)
    if not res:
        return Result.error(f"Failed to fetch data at {path}", res)

    return Ok({"label": res.unwrapped})
```
