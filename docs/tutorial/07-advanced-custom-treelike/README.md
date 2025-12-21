# Step 7: Advanced - Custom TreeLike Implementation

This advanced tutorial shows how to create a **custom data provider** by implementing the `TreeLike` interface. This lets you connect Ymery to any data source!

## What You'll Learn

- The TreeLike interface and its methods
- How to create a custom data provider plugin
- How to register your provider with Ymery
- Real-world use cases

## The TreeLike Interface

All data in Ymery flows through the `TreeLike` interface:

```python
class TreeLike(ABC):
    @abstractmethod
    def get_metadata(self, key: str) -> Result[Any]:
        """Get a metadata value by key"""
        pass

    @abstractmethod
    def set_metadata(self, key: str, value: Any) -> Result[None]:
        """Set a metadata value"""
        pass

    @abstractmethod
    def get_child(self, name: str) -> Result['TreeLike']:
        """Get a child node by name"""
        pass

    @abstractmethod
    def get_children(self) -> Result[Dict[str, 'TreeLike']]:
        """Get all children"""
        pass

    @abstractmethod
    def add_child(self, name: str, metadata: Dict[str, Any]) -> Result['TreeLike']:
        """Add a new child node"""
        pass
```

## Example: Weather Data Provider

Let's create a provider that exposes weather data:

### File: `plugins/weather_provider.py`

```python
"""
Weather Data Provider - A custom TreeLike implementation
that provides weather data for cities.
"""

from typing import Dict, Any, Optional
from ymery.backend.tree_like import TreeLike
from ymery.result import Result, Ok
from ymery.decorators import tree_like

# Simulated weather data (in real app, fetch from API)
WEATHER_DATA = {
    "new-york": {"label": "New York", "temp": 72, "condition": "Sunny", "humidity": 45},
    "london": {"label": "London", "temp": 58, "condition": "Cloudy", "humidity": 78},
    "tokyo": {"label": "Tokyo", "temp": 68, "condition": "Rainy", "humidity": 85},
    "paris": {"label": "Paris", "temp": 65, "condition": "Partly Cloudy", "humidity": 55},
}


@tree_like
class WeatherProvider(TreeLike):
    """
    Provides weather data as a tree structure.

    Usage in YAML:
        data:
          weather:
            type: weather-provider
    """

    def __init__(self, city_id: Optional[str] = None):
        self._city_id = city_id
        self._metadata: Dict[str, Any] = {}

        if city_id is None:
            # Root node
            self._metadata = {"label": "Weather Data"}
        elif city_id in WEATHER_DATA:
            # City node
            self._metadata = WEATHER_DATA[city_id].copy()
        else:
            self._metadata = {"label": "Unknown"}

    def get_metadata(self, key: str) -> Result[Any]:
        if key in self._metadata:
            return Ok(self._metadata[key])
        return Result.error(f"Metadata key '{key}' not found")

    def set_metadata(self, key: str, value: Any) -> Result[None]:
        self._metadata[key] = value
        return Ok(None)

    def get_child(self, name: str) -> Result['TreeLike']:
        if self._city_id is None:
            # Root can get city children
            if name in WEATHER_DATA:
                return Ok(WeatherProvider(name))
        return Result.error(f"Child '{name}' not found")

    def get_children(self) -> Result[Dict[str, 'TreeLike']]:
        if self._city_id is None:
            # Root returns all cities
            children = {
                city_id: WeatherProvider(city_id)
                for city_id in WEATHER_DATA
            }
            return Ok(children)
        # City nodes have no children
        return Ok({})

    def add_child(self, name: str, metadata: Dict[str, Any]) -> Result['TreeLike']:
        # This provider is read-only
        return Result.error("Weather provider is read-only")
```

### File: `app.yaml`

```yaml
data:
  weather:
    type: weather-provider

widgets:
  main-window:
    type: imgui-main-window
    label: "Weather App"
    body:
      - text:
          label: "World Weather"
      - separator:

      # Display weather tree
      - data-path: $weather
        builtin.tree-view:

      - separator:

      # Custom display for each city
      - data-path: $weather
        body:
          foreach-child:
            - collapsing-header:
                label: "@label"
                body:
                  - text:
                      label: "Temperature: @temp°F"
                  - text:
                      label: "Condition: @condition"
                  - text:
                      label: "Humidity: @humidity%"

app:
  widget: app.main-window
  main-data: weather
```

## Plugin Registration

To use your custom provider, register it as a plugin:

### File: `plugins/__init__.py`

```python
# This file makes the plugins directory a Python package
```

### Running with Custom Plugins

```bash
uv run ymery --layouts-path . --plugins-path ./plugins --main app
```

## Real-World Use Cases

### 1. Database Connection

```python
@tree_like
class DatabaseProvider(TreeLike):
    """Connect to a database and expose tables as tree nodes"""

    def __init__(self, connection_string: str):
        self._conn = connect(connection_string)

    def get_children(self) -> Result[Dict[str, 'TreeLike']]:
        tables = self._conn.get_tables()
        return Ok({t.name: TableNode(t) for t in tables})
```

### 2. File System Browser

```python
@tree_like
class FileSystemProvider(TreeLike):
    """Browse the file system as a tree"""

    def __init__(self, path: str = "/"):
        self._path = Path(path)

    def get_children(self) -> Result[Dict[str, 'TreeLike']]:
        if not self._path.is_dir():
            return Ok({})
        children = {}
        for item in self._path.iterdir():
            children[item.name] = FileSystemProvider(str(item))
        return Ok(children)
```

### 3. REST API Integration

```python
@tree_like
class RestApiProvider(TreeLike):
    """Fetch data from a REST API"""

    def __init__(self, endpoint: str):
        self._endpoint = endpoint
        self._cache = None

    def _fetch(self):
        if self._cache is None:
            response = requests.get(self._endpoint)
            self._cache = response.json()
        return self._cache
```

### 4. System Monitor (like the Kernel demo)

```python
@tree_like
class SystemMonitor(TreeLike):
    """Monitor system resources in real-time"""

    def get_metadata(self, key: str) -> Result[Any]:
        if key == "cpu":
            return Ok(f"{psutil.cpu_percent()}%")
        if key == "memory":
            return Ok(f"{psutil.virtual_memory().percent}%")
        # ...
```

## The `@tree_like` Decorator

The decorator registers your class with Ymery:

```python
from ymery.decorators import tree_like

@tree_like
class MyProvider(TreeLike):
    pass

# Now usable in YAML as:
# data:
#   my-data:
#     type: my-provider
```

The type name is derived from the class name:
- `MyProvider` → `my-provider`
- `WeatherDataSource` → `weather-data-source`

## Constructor Arguments

Pass arguments via `arg:` in YAML:

```python
@tree_like
class ConfigurableProvider(TreeLike):
    def __init__(self, source: str, refresh_rate: int = 60):
        self._source = source
        self._refresh_rate = refresh_rate
```

```yaml
data:
  my-data:
    type: configurable-provider
    arg:
      source: "https://api.example.com"
      refresh-rate: 30
```

## Running the Example

This tutorial includes a simple example that simulates a system monitor:

```bash
./run.sh
```

## Exercises

1. Create a `TodoApiProvider` that fetches from JSONPlaceholder API
2. Build a `ConfigFileProvider` that reads from YAML/JSON config files
3. Implement a `GitRepoProvider` that shows git branches and commits
4. Create a caching layer for slow data sources

## Summary

You've now learned:
- The fundamentals of Ymery's declarative UI system
- Data binding with trees and references
- Event handling and dynamic data
- HelloImGui docking and menus
- Modular project organization
- Custom data providers

**Congratulations!** You're ready to build powerful applications with Ymery!

---

[← Previous: Step 6 - Modular Structure](../06-modular-structure/README.md) | [Back to Tutorial Index →](../README.md)
