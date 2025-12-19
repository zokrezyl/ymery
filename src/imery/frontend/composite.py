"""
Composite widgets - containers for other widgets
"""

from imery.frontend.widget import Widget
from imery.decorators import widget
from imery.types import DataPath
from imery.result import Result, Ok

from typing import List


@widget
class Composite(Widget):
    """Composite widget - contains list of child widgets"""

    def init(self) -> Result[None]:
        self._child_groups = {}

        res = super().init()
        if not res:
            return res

        # Read body to determine number of groups
        res = self._data_bag.get_static("body")
        if not res:
            return Result.error("Composite.init: failed to get body", res)
        body = res.unwrapped

        # Normalize body to list
        if body is None:
            return Ok(None)
        if isinstance(body, (str, dict)):
            body = [body]
        elif not isinstance(body, list):
            return Result.error(f"Composite.init: body must be string, dict, or list, got {type(body)}")

        # Initialize empty dict for each body item index
        self._child_groups = {i: {} for i in range(len(body))}
        return Ok(None)



    @property
    def is_empty(self) -> Result[bool]:
        """Check if composite has no children"""
        res = self._ensure_children()
        if not res:
            return Result.error("could not init children", res)
        # Check if all groups are empty
        for group in self._child_groups.values():
            if len(group) > 0:
                return Ok(False)
        return Ok(True)

    @property
    def children(self) -> Result[List]:
        """Get all child widgets as flat list"""
        res = self._ensure_children()
        if not res:
            return Result.error("could not init children")
        result = []
        for group in self._child_groups.values():
            result.extend(group.values())
        return Ok(result)

    def _substitute_variables(self, spec, key, value):
        """
        Recursively substitute $key and $value in a widget spec.

        Args:
            spec: Widget specification (string, dict, list, or primitive)
            key: The key to substitute for $key
            value: The value to substitute for $value

        Returns:
            Substituted spec (same type as input)
        """
        if isinstance(spec, str):
            # Substitute $key and $value in string
            result = spec.replace("$key", str(key))
            result = result.replace("$value", str(value))
            return result
        elif isinstance(spec, dict):
            # Recursively substitute in dict values
            return {k: self._substitute_variables(v, key, value) for k, v in spec.items()}
        elif isinstance(spec, list):
            # Recursively substitute in list items
            return [self._substitute_variables(item, key, value) for item in spec]
        else:
            # Primitives (int, float, bool, None) - return as-is
            return spec

    def _ensure_children(self) -> Result[None]:
        """Sync child widgets with data - creates new, reuses existing, garbage collects removed"""
        res = self._data_bag.get_static("body")
        if not res:
            self._handle_error(Result.error("Composite: _ensure_children: failed to get body", res))
            return Ok(None)
        body = res.unwrapped
        if body is None:
            return Ok(None)

        # Normalize body to list
        if isinstance(body, (str, dict)):
            body = [body]
        elif not isinstance(body, list):
            self._handle_error(Result.error(f"Composite body must be string, dict, or list, got {type(body)}"))
            return Ok(None)

        for i, item in enumerate(body):
            old_group = self._child_groups.get(i, {})

            # foreach-key-value (also support foreach-key for compatibility)
            foreach_key = None
            if isinstance(item, dict):
                if "foreach-key-value" in item:
                    foreach_key = "foreach-key-value"
                elif "foreach-key" in item:
                    foreach_key = "foreach-key"

            if foreach_key:
                if len(item) != 1:
                    self._handle_error(Result.error(f"Composite {foreach_key} item must have only '{foreach_key}' key, got {list(item.keys())}"))
                    continue

                foreach_body = item[foreach_key]
                widget_spec = foreach_body[0] if isinstance(foreach_body, list) else foreach_body

                metadata_res = self._data_bag.get_metadata()
                if not metadata_res:
                    self._handle_error(Result.error(f"Composite: {foreach_key} failed to get metadata", metadata_res))
                    continue
                metadata = metadata_res.unwrapped
                if not isinstance(metadata, dict):
                    self._handle_error(Result.error(f"Composite: {foreach_key} requires metadata to be dict, got {type(metadata)}"))
                    continue

                new_group = {}
                for key in metadata.keys():
                    if key in old_group:
                        new_group[key] = old_group[key]
                    else:
                        value = metadata[key]
                        substituted_spec = self._substitute_variables(widget_spec, key, value)
                        res = self._create_widget_from_spec(substituted_spec)
                        if res:
                            new_group[key] = res.unwrapped
                        else:
                            self._handle_error(Result.error(f"Composite: {foreach_key} failed to create widget for key '{key}'", res))
                self._child_groups[i] = new_group
                continue

            # foreach-child: rebuild dict with data children
            if isinstance(item, dict) and "foreach-child" in item:
                if len(item) != 1:
                    self._handle_error(Result.error(f"Composite foreach-child item must have only 'foreach-child' key, got {list(item.keys())}"))
                    continue

                foreach_body = item["foreach-child"]
                widget_spec = foreach_body[0] if isinstance(foreach_body, list) else foreach_body

                res = self._data_bag.get_children_names()
                if not res:
                    self._handle_error(Result.error(f"Composite: foreach-child failed to get children", res))
                    continue
                child_names = res.unwrapped

                new_group = {}
                for child_name in child_names:
                    if child_name in old_group:
                        new_group[child_name] = old_group[child_name]
                    else:
                        res = self._create_widget_from_spec(widget_spec, child_name)
                        if res:
                            new_group[child_name] = res.unwrapped
                        else:
                            self._handle_error(Result.error(f"Composite: foreach-child failed to create widget for '{child_name}'", res))
                self._child_groups[i] = new_group
                continue

            # Single widget: create if not exists
            if "_single" in old_group:
                continue

            if isinstance(item, str):
                widget_name = item
                params = None
                path_spec = None
            elif isinstance(item, dict):
                path_spec = item.get("data-path")

                widget_keys = [k for k in item.keys() if k != "data-path"]
                if len(widget_keys) != 1:
                    self._handle_error(Result.error(f"Composite template item must have one widget key (plus optional data-path), got {len(widget_keys)}: {widget_keys}"))
                    continue
                widget_name = widget_keys[0]
                params = item[widget_name]
            else:
                self._handle_error(Result.error(f"Composite template item must be str or dict, got {type(item)}"))
                continue

            if '.' not in widget_name and self._namespace:
                full_widget_name = f"{self._namespace}.{widget_name}"
            else:
                full_widget_name = widget_name

            # Create child DataBag with inherited path
            res = self._data_bag.inherit(path_spec, params)
            if not res:
                self._handle_error(Result.error(f"Composite: failed to create child DataBag for '{widget_name}'", res))
                continue
            child_bag = res.unwrapped

            res = self._factory.create_widget_from_bag(full_widget_name, child_bag)
            if not res:
                self._handle_error(Result.error(f"Composite: failed to create child widget '{widget_name}'", res))
                continue

            child = res.unwrapped
            if child.__class__.__name__ == "Popup":
                self._handle_error(Result.error(f"Popup '{widget_name}' cannot be child of Composite"))
                continue

            self._child_groups[i] = {"_single": child}

        return Ok(None)

    def _create_widget_from_spec(self, spec, path_spec=None):
        """Create a widget from a spec (string or dict)"""
        if isinstance(spec, str):
            widget_name = spec
            widget_params = None
        elif isinstance(spec, dict):
            if len(spec) != 1:
                return Result.error(f"Widget spec must have one key, got {len(spec)}")
            widget_name = list(spec.keys())[0]
            widget_params = spec[widget_name]
        else:
            return Result.error(f"Widget spec must be str or dict, got {type(spec)}")

        if '.' not in widget_name and self._namespace:
            full_widget_name = f"{self._namespace}.{widget_name}"
        else:
            full_widget_name = widget_name

        # Create child DataBag with inherited path
        res = self._data_bag.inherit(path_spec, widget_params)
        if not res:
            return Result.error(f"Failed to create child DataBag for '{widget_name}'", res)
        child_bag = res.unwrapped

        res = self._factory.create_widget_from_bag(full_widget_name, child_bag)
        if not res:
            return Result.error(f"Failed to create widget '{widget_name}'", res)

        child = res.unwrapped
        if child.__class__.__name__ == "Popup":
            return Result.error(f"Popup '{widget_name}' cannot be child of Composite")

        return Ok(child)

    def render(self) -> Result[None]:
        """Render all children - Composite doesn't use head/body pattern"""
        # Check if data children changed (for foreach-child refresh)
        self._ensure_children()

        # Push styles before rendering children
        res = self._push_styles()
        if not res:
            self._handle_error(Result.error("Composite: _push_styles failed", res))

        for _, child_group in self._child_groups.items():
            for _, child in child_group.items():
                res = child.render()
                if not res:
                    self._handle_error(Result.error(f"Composite: child render failed", res))

        # Pop styles after rendering children
        res = self._pop_styles()
        if not res:
            self._handle_error(Result.error("Composite: _pop_styles failed", res))

        return self._render_errors()


    def dispose(self) -> Result[None]:
        """Dispose all children"""
        self._child_groups = {}
        return Ok(None)

