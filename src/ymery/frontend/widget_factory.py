from pathlib import Path
from ymery.types import TreeLike, DataPath, Object
from ymery.data_bag import DataBag
from ymery.dispatcher import Dispatcher
from ymery.result import Result, Ok
from ymery.plugin_manager import PluginManager
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

    def __init__(self, dispatcher: Dispatcher, plugin_manager: PluginManager, widget_definitions: Dict[str, dict], data_trees: Dict = None, widgets_path: Optional[str] = None):
        """
        Args:
            dispatcher: Event dispatcher
            widget_definitions: Dictionary of widget_name -> widget definition from Lang
            data_trees: Dictionary of data_name -> data tree from layouts
            widgets_path: Colon-separated list of directories to search for widget modules
        """
        super().__init__()
        self._dispatcher = dispatcher
        self._plugin_manager = plugin_manager
        self._widget_cache = {}  # Cache of primitive + YAML widget definitions
        self._widgets_path = widgets_path
        self._data_trees = data_trees or {}

        # Store YAML widget definitions from Lang
        self._widget_definitions = widget_definitions

    def init(self) -> Result[None]:
        # Populate widget_cache from plugin_manager
        res = self._plugin_manager.get_children_names(DataPath("/widget"))
        if not res:
            return Result.error("WidgetFactory: failed to get widget names from plugin_manager", res)

        for registered_name in res.unwrapped:
            res = self._plugin_manager.get_metadata(DataPath(f"/widget/{registered_name}"))
            if not res:
                return Result.error(f"WidgetFactory: failed to get metadata for widget '{registered_name}'", res)
            metadata = res.unwrapped
            self._widget_cache[registered_name] = metadata["class"]

        # Populate widget_cache from widget_definitions (YAML definitions)
        for widget_name, widget_def in self._widget_definitions.items():
            self._widget_cache[widget_name] = widget_def

        return Ok(None)

    def create_widget_from_bag(self, widget_name: str, data_bag: DataBag) -> Result["Widget"]:
        """
        Create widget from widget_name using a pre-created DataBag.

        Args:
            widget_name: Widget name (e.g., "demo_widgets.demo-form", "text", "button")
            data_bag: DataBag with data context for the widget

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
            widget_only = lookup_name.split('.')[-1]
            if widget_only in self._widget_cache:
                cached_item = self._widget_cache[widget_only]
                lookup_name = widget_only

        if cached_item is None:
            return Result.error(f"Widget '{widget_name}' not found in cache")

        # Check if it's a widget class
        if isinstance(cached_item, type):
            return cached_item.create(
                factory=self,
                dispatcher=self._dispatcher,
                namespace=namespace,
                data_bag=data_bag
            )
        elif isinstance(cached_item, dict) and "type" in cached_item:
            # YAML widget definition
            widget_type = cached_item["type"]
            if widget_type not in self._widget_cache:
                return Result.error(f"Widget type '{widget_type}' not found in cache")

            widget_class = self._widget_cache[widget_type]
            if not isinstance(widget_class, type):
                return Result.error(f"Widget type '{widget_type}' is not a class")

            # For YAML widgets, merge cached_item into data_bag's static
            if data_bag._static is None:
                data_bag._static = dict(cached_item)
            else:
                merged = dict(cached_item)
                merged.update(data_bag._static)
                data_bag._static = merged

            return widget_class.create(
                factory=self,
                dispatcher=self._dispatcher,
                namespace=namespace,
                data_bag=data_bag
            )
        else:
            return Result.error(f"WidgetFactory: cached_item must be a class or dict with 'type', got {type(cached_item)}")

    def create_widget(self, widget_name: str, tree_like: TreeLike, data_path: DataPath, params=None, parent_data_trees=None) -> Result["Widget"]:
        """
        Create widget from widget_name

        Args:
            widget_name: Widget name (e.g., "demo_widgets.demo-form", "text", "button")
            tree_like: TreeLike instance (can be None) - used as main data tree
            data_path: DataPath to data
            params: Parameters for the widget (can be None) - used as static
            parent_data_trees: Optional data_trees from parent widget (for inheriting local, etc.)

        Returns:
            Result[Widget]: Created widget instance
        """
        # Create data_trees dict with tree_like as main entry
        data_trees = dict(self._data_trees)
        if parent_data_trees:
            for key, value in parent_data_trees.items():
                if key not in data_trees:
                    data_trees[key] = value
        if tree_like:
            data_trees["main"] = tree_like
        main_data_key = "main" if tree_like else None

        static = params if params is not None else {}
        data_bag = DataBag(self._dispatcher, self._plugin_manager, data_trees, main_data_key, data_path, static)

        return self.create_widget_from_bag(widget_name, data_bag)

    def dispose(self) -> Result[None]:
        return Ok(None)
