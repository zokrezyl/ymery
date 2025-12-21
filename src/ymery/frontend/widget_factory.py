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
e
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

    def create_widget(self, parent_data_bag: DataBag, statics, namespace: str = "") -> Result["Widget"]:
        """
        Create a widget from a widget specification.

        Args:
            parent_data_bag: Parent's DataBag to inherit from
            _statics: Widget specification in one of these forms:
                      - str: widget name (e.g., "text", "button", "demo.my-popup")
                      - dict with single key: {widget_name: statics_dict}
                        e.g., {"button": {"label": "Click me"}}
                      - list: composite body, creates a composite widget
                        e.g., [{"text": "Hello"}, {"button": {"label": "OK"}}]
            namespace: Current namespace for resolving unqualified widget names

        Returns:
            Result[Widget]: Created widget instance

        Why "_statics"?
            Called "statics" because these are the STATIC definitions from YAML that
            don't change at runtime. They define the widget's structure (body, type),
            behavior (event-handlers), appearance (style), and data bindings (data,
            main-data, data-path). 

        The factory:
        1. Parses _statics to extract widget_name and statics dict
        2. Extracts data-path from statics
        3. Calls parent_data_bag.inherit(data_path, statics) to create child DataBag
           - inherit() copies _data_trees dict (isolation between siblings)
           - inherit() calls DataBag.create() which calls init()
           - init() processes statics['data'] to add local trees
           - init() processes statics['main-data'] to override main data
        4. Looks up widget class from cache (primitive or YAML-defined)
        5. Merges YAML widget definition with statics
        6. Calls widget_class.create(factory, dispatcher, namespace, data_bag)
        """
        # Parse statics to get widget_name and widget_statics dict
        if isinstance(statics, str):
            # String → widget name only
            widget_name = statics
            widget_statics = None
        elif isinstance(statics, dict):
            # Dict → {widget_name: widget_statics} with optional data-path
            # data-path is a special key that's NOT the widget name
            special_keys = {"data-path"}
            widget_keys = [k for k in statics.keys() if k not in special_keys]

            if len(widget_keys) != 1:
                return Result.error(f"create_widget: dict must have exactly one widget key (plus optional data-path), got {len(widget_keys)}: {widget_keys}")

            widget_name = widget_keys[0]
            widget_statics = statics[widget_name]

            # Ensure widget_statics is a dict or None
            if widget_statics is not None and not isinstance(widget_statics, dict):
                # Could be a simple value like {"text": "Hello"} where "Hello" is the label
                widget_statics = {"label": widget_statics} if isinstance(widget_statics, (str, int, float, bool)) else None

            # Copy data-path into widget_statics if present
            if "data-path" in statics:
                if widget_statics is None:
                    widget_statics = {}
                else:
                    widget_statics = dict(widget_statics)  # Don't mutate original
                widget_statics["data-path"] = statics["data-path"]
        elif isinstance(statics, list):
            # List → composite body
            widget_name = "composite"
            widget_statics = {"type": "composite", "body": statics}
        else:
            return Result.error(f"create_widget: invalid statics type: {type(statics)}")

        # Add namespace if not qualified
        if '.' not in widget_name and namespace:
            widget_name = f"{namespace}.{widget_name}"

        # Extract data-path from widget_statics if present
        data_path = widget_statics.get("data-path") if widget_statics else None

        # Create child DataBag via inherit (handles data:, main-data:, copies _data_trees)
        res = parent_data_bag.inherit(data_path, widget_statics)
        if not res:
            return Result.error(f"create_widget: failed to inherit DataBag for '{widget_name}'", res)
        data_bag = res.unwrapped

        # Extract namespace from widget_name if present
        if '.' in widget_name:
            widget_namespace = widget_name.rsplit('.', 1)[0]
            lookup_name = widget_name
        else:
            widget_namespace = namespace
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

        # Check if it's a widget class (primitive widget)
        if isinstance(cached_item, type):
            return cached_item.create(
                widget_factory=self,
                dispatcher=self._dispatcher,
                namespace=widget_namespace,
                data_bag=data_bag
            )
        elif isinstance(cached_item, dict) and "type" in cached_item:
            # YAML widget definition - merge with statics
            widget_type = cached_item["type"]
            if widget_type not in self._widget_cache:
                return Result.error(f"Widget type '{widget_type}' not found in cache")

            widget_class = self._widget_cache[widget_type]
            if not isinstance(widget_class, type):
                return Result.error(f"Widget type '{widget_type}' is not a class")

            # Merge cached_item (YAML definition) with data_bag's statics
            # statics from caller override YAML definition
            if data_bag._static is None:
                data_bag._static = dict(cached_item)
            else:
                merged = dict(cached_item)
                merged.update(data_bag._static)
                data_bag._static = merged

            return widget_class.create(
                widget_factory=self,
                dispatcher=self._dispatcher,
                namespace=widget_namespace,
                data_bag=data_bag
            )
        else:
            return Result.error(f"WidgetFactory: cached_item must be a class or dict with 'type', got {type(cached_item)}")

    def dispose(self) -> Result[None]:
        return Ok(None)
