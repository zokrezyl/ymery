from pathlib import Path
from imery.types import TreeLike, DataPath, Object
from imery.data_bag import DataBag
from imery.dispatcher import Dispatcher
from imery.result import Result, Ok
import importlib.util
import sys

from typing import Optional, Dict


def to_pascal_case(name: str) -> str:
    """Convert hyphenated name to PascalCase (e.g., 'same-line' -> 'SameLine')"""
    return ''.join(part.capitalize() for part in name.split('-'))

def to_kebab_case(name: str) -> str:
    """Convert PascalCase to kebab-case (e.g., 'SameLine' -> 'same-line')"""
    result = []
    for i, char in enumerate(name):
        if char.isupper() and i > 0:
            result.append('-')
        result.append(char.lower())
    return ''.join(result)


class WidgetFactory(Object):
    """
    Factory for creating widgets

    Uses DataBag for data access and creates appropriate Widget subclasses
    """

    def __init__(self, dispatcher: Dispatcher, widget_definitions: Dict[str, dict], data_trees: Dict = None, widgets_path: Optional[str] = None):
        """
        Args:
            dispatcher: Event dispatcher
            widget_definitions: Dictionary of widget_name -> widget definition from Lang
            data_trees: Dictionary of data_name -> data tree from layouts
            widgets_path: Colon-separated list of directories to search for widget modules
        """
        super().__init__()
        self._dispatcher = dispatcher
        self._widget_cache = {}  # Cache of primitive + YAML widget definitions
        self._widgets_path = widgets_path
        self._data_trees = data_trees or {}

        # Store YAML widget definitions from Lang
        self._widget_definitions = widget_definitions

    def init(self) -> Result[None]:
        """Load widget classes dynamically from widgets_path"""
        from imery.frontend.decorators import _pending_widgets

        # Build list of widget directories from colon-separated path
        widget_dirs = []
        if self._widgets_path:
            # Parse colon-separated paths
            for path_str in self._widgets_path.split(':'):
                path_str = path_str.strip()
                if path_str:
                    widget_dirs.append(Path(path_str))
        else:
            # Default: Get directory relative to this file (imery/frontend/widgets)
            frontend_dir = Path(__file__).parent
            widget_dirs.append(frontend_dir / "widgets")

        # Scan each widget directory and load modules
        for widgets_dir in widget_dirs:
            if not widgets_dir.exists():
                continue

            # Add parent directory to sys.path for proper imports
            parent_dir = str(widgets_dir.parent.absolute())
            if parent_dir not in sys.path:
                sys.path.insert(0, parent_dir)

            # Scan all .py files in the widgets directory
            for widget_file in widgets_dir.iterdir():
                if not widget_file.is_file():
                    continue
                if not widget_file.name.endswith('.py'):
                    continue
                if widget_file.name.startswith('_'):
                    continue

                widget_module_name = widget_file.stem

                try:
                    # Load the module dynamically

                    # Use widgets directory name + module name for package
                    package_name = f"{widgets_dir.name}.{widget_module_name}"

                    spec = importlib.util.spec_from_file_location(
                        package_name,
                        widget_file
                    )
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[spec.name] = module
                    spec.loader.exec_module(module)

                except Exception as e:
                    return Result.error(f"WidgetFactory: init: Could not load {widget_file}", e)

        # Now collect all registered widgets from _pending_widgets
        for widget_class in _pending_widgets:
            # Convert class name to kebab-case for cache key
            class_name = widget_class.__name__
            widget_name = to_kebab_case(class_name)
            self._widget_cache[widget_name] = widget_class

        # Add YAML widgets to cache
        self._widget_cache.update(self._widget_definitions)

        return Ok(None)

    def create_widget(self, widget_name: str, tree_like: TreeLike, data_path: DataPath, params=None) -> Result["Widget"]:
        """
        Create widget from widget_name

        Args:
            widget_name: Widget name (e.g., "demo_widgets.demo-form", "text", "button")
            tree_like: TreeLike instance (can be None) - used as main data tree
            data_path: DataPath to data
            params: Parameters for the widget (can be None) - used as static

        Returns:
            Result[Widget]: Created widget instance
        """
        # Extract namespace if present
        if '.' in widget_name:
            namespace = widget_name.rsplit('.', 1)[0]
            lookup_name = widget_name
        else:
            namespace = ""
            lookup_name = widget_name

        # Smart lookup: try with full name first, then without namespace (for primitives)
        cached_item = None
        if lookup_name in self._widget_cache:
            cached_item = self._widget_cache[lookup_name]
        elif '.' in lookup_name:
            # Try without namespace (e.g., "demo_widgets.text" -> "text")
            widget_only = lookup_name.split('.')[-1]
            if widget_only in self._widget_cache:
                cached_item = self._widget_cache[widget_only]
                lookup_name = widget_only

        if cached_item is None:
            return Result.error(f"Widget '{widget_name}' not found in cache")

        # Create data_trees dict with tree_like as main entry
        # Use "main" as default key if tree_like is provided
        data_trees = dict(self._data_trees)  # Copy factory's data_trees
        if tree_like:
            data_trees["main"] = tree_like
        main_data_key = "main" if tree_like else None

        # Check if it's a widget class (registered via @widget decorator or cached)
        if isinstance(cached_item, type):
            # It's a widget class - create DataBag and call create()
            static = params if params is not None else {}
            data_bag = DataBag(data_trees, main_data_key, data_path, static)
            return cached_item.create(
                factory=self,
                dispatcher=self._dispatcher,
                namespace=namespace,
                data_bag=data_bag
            )
        elif isinstance(cached_item, dict) and "type" in cached_item:
            # YAML widget definition: {"type": "...", "body": ..., other metadata...}
            widget_type = cached_item["type"]

            # Look up the widget class by type
            if widget_type not in self._widget_cache:
                return Result.error(f"Widget type '{widget_type}' not found in cache")

            widget_class = self._widget_cache[widget_type]
            if not isinstance(widget_class, type):
                return Result.error(f"Widget type '{widget_type}' is not a class")

            # Merge params with cached_item (params override cached_item)
            static = dict(cached_item)
            if params:
                static.update(params)
            data_bag = DataBag(data_trees, main_data_key, data_path, static)
            return widget_class.create(
                factory=self,
                dispatcher=self._dispatcher,
                namespace=namespace,
                data_bag=data_bag
            )
        else:
            # Old format: list (backward compatibility) - treat as composite body
            if "composite" not in self._widget_cache:
                return Result.error("Composite widget not found in cache")

            composite_class = self._widget_cache["composite"]
            data_bag = DataBag(data_trees, main_data_key, data_path, cached_item)
            return composite_class.create(
                factory=self,
                dispatcher=self._dispatcher,
                namespace=namespace,
                data_bag=data_bag
            )

    def dispose(self) -> Result[None]:
        return Ok(None)
