"""
Composite widgets - containers for other widgets
"""

from imery.frontend.widget import Widget
from imery.frontend.decorators import widget
from imery.backend.types import TreeLike
from imery.types import DataPath
from imery.result import Result, Ok

from typing import Optional, List

import pprint


@widget
class Composite(Widget):
    """Composite widget - contains list of child widgets"""

    def init(self) -> Result[None]:
        res = super().init()
        self._children: Optional[List] = None
        return res



    @property
    def is_empty(self) -> Result[bool]:
        """Check if composite has no children"""
        if self._children is None:
            res = self._init_children()
            if not res:
                return Result.error("could not init children")
        return len(self._children) == 0

    @property
    def children(self) -> Result[bool]:
        """Check if composite has no children"""
        if self._children is None:
            res = self._init_children()
            if not res:
                return Result.error("could not init children")
        return Ok(self._children)

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

    def _init_children(self) -> Result[None]:
        """Create all child widgets from body"""
        # Extract body from params
        self._children = []
        static = self._data_bag._static
        if isinstance(static, dict) and "body" in static:
            body = static["body"]
        elif isinstance(static, list):
            body = static
        else:
            pprint.pp(static)
            return Result.error(f"Composite params must be dict with 'body' or list, got {type(static)}, {static}")

        # Normalize body to always be a list (handle collapsed forms)
        if isinstance(body, str):
            # Collapsed: body: "text" → ["text"]
            body = [body]
        elif isinstance(body, dict):
            # Collapsed: body: {text: null} → [{text: null}]
            body = [body]
        elif not isinstance(body, list):
            return Result.error(f"Composite body must be string, dict, or list, got {type(body)}")

        for item in body:
            # Check for foreach-key keyword
            if isinstance(item, dict) and "foreach-key" in item:
                # Validate foreach-key dict has only "foreach-key" key (no garbage)
                if len(item) != 1:
                    return Result.error(f"Composite foreach-key item must have only 'foreach-key' key, got {list(item.keys())}")

                # This is a foreach-key item - iterate over metadata keys
                foreach_body = item["foreach-key"]

                # Normalize foreach_body to list (handle collapsed forms)
                if isinstance(foreach_body, str):
                    # Collapsed: foreach-key: "text" → ["text"]
                    foreach_widgets = [foreach_body]
                elif isinstance(foreach_body, dict):
                    # Collapsed: foreach-key: {text: null} → [{text: null}]
                    foreach_widgets = [foreach_body]
                elif isinstance(foreach_body, list):
                    foreach_widgets = foreach_body
                else:
                    return Result.error(f"Composite foreach-key body must be string, dict, or list, got {type(foreach_body)}")

                # Get metadata at current path
                data_path = self._data_bag._main_data_path
                metadata_res = self._data_bag.get_metadata()
                if not metadata_res:
                    return Result.error(f"Composite: foreach-key failed to get metadata at path '{data_path}'", metadata_res)

                metadata = metadata_res.unwrapped

                # Iterate over metadata keys
                if not isinstance(metadata, dict):
                    return Result.error(f"Composite: foreach-key requires metadata to be dict, got {type(metadata)}")

                for key in metadata.keys():
                    value = metadata[key]

                    # Create each widget in the foreach-key body
                    for widget_spec in foreach_widgets:
                        # Substitute $key and $value in widget_spec
                        substituted_spec = self._substitute_variables(widget_spec, key, value)

                        if isinstance(substituted_spec, str):
                            widget_name = substituted_spec
                            widget_params = None
                        elif isinstance(substituted_spec, dict):
                            if len(substituted_spec) != 1:
                                return Result.error(f"Composite foreach-key item must have one key, got {len(substituted_spec)}")
                            widget_name = list(substituted_spec.keys())[0]
                            widget_params = substituted_spec[widget_name]
                        else:
                            return Result.error(f"Composite foreach-key item must be str or dict, got {type(substituted_spec)}")

                        # Prepend namespace if needed
                        if '.' not in widget_name and self._namespace:
                            full_widget_name = f"{self._namespace}.{widget_name}"
                        else:
                            full_widget_name = widget_name

                        # Create widget at current path (not child path!)
                        tree_like = self._data_bag._main_data_tree
                        res = self._factory.create_widget(full_widget_name, tree_like, data_path, widget_params, self._data_bag._data_trees)
                        if not res:
                            return Result.error(f"Composite: foreach-key failed to create widget '{widget_name}'", res)

                        child = res.unwrapped
                        if child.__class__.__name__ == "Popup":
                            return Result.error(f"Popup '{widget_name}' cannot be child of Composite foreach-key")
                        self._children.append(child)

                # Continue to next item in body
                continue

            # Check for foreach-child keyword
            if isinstance(item, dict) and "foreach-child" in item:
                # Validate foreach dict has only "foreach" key (no garbage)
                if len(item) != 1:
                    return Result.error(f"Composite foreach item must have only 'foreach-child' key, got {list(item.keys())}")

                # This is a foreach item - iterate over children
                foreach_body = item["foreach-child"]

                # Normalize foreach_body to list (handle collapsed forms)
                if isinstance(foreach_body, str):
                    # Collapsed: foreach: "text" → ["text"]
                    foreach_widgets = [foreach_body]
                elif isinstance(foreach_body, dict):
                    # Collapsed: foreach: {text: null} → [{text: null}]
                    foreach_widgets = [foreach_body]
                elif isinstance(foreach_body, list):
                    foreach_widgets = foreach_body
                else:
                    return Result.error(f"Composite foreach body must be string, dict, or list, got {type(foreach_body)}")

                # Get children at current path
                tree_like = self._data_bag._main_data_tree
                data_path = self._data_bag._main_data_path
                res = tree_like.get_children_names(data_path)
                if not res:
                    return Result.error(f"Composite: foreach failed to get children at path '{data_path}'", res)

                child_names = res.unwrapped

                # For each child, create the foreach body widgets
                for child_name in child_names:
                    child_path = data_path / child_name

                    # Create each widget in the foreach body at child_path
                    for widget_spec in foreach_widgets:
                        if isinstance(widget_spec, str):
                            widget_name = widget_spec
                            widget_params = None
                        elif isinstance(widget_spec, dict):
                            if len(widget_spec) != 1:
                                return Result.error(f"Composite foreach item must have one key, got {len(widget_spec)}")
                            widget_name = list(widget_spec.keys())[0]
                            widget_params = widget_spec[widget_name]
                        else:
                            return Result.error(f"Composite foreach item must be str or dict, got {type(widget_spec)}")

                        # Prepend namespace if needed
                        if '.' not in widget_name and self._namespace:
                            full_widget_name = f"{self._namespace}.{widget_name}"
                        else:
                            full_widget_name = widget_name

                        # Create widget at child_path
                        res = self._factory.create_widget(full_widget_name, tree_like, child_path, widget_params, self._data_bag._data_trees)
                        if not res:
                            return Result.error(f"Composite: foreach failed to create widget '{widget_name}' at '{child_path}'", res)

                        child = res.unwrapped
                        if child.__class__.__name__ ==  "Popup":
                            return Result.error(f"Popup '{widget_name}' cannot be child of Composite foreach")
                        self._children.append(child)

                # Continue to next item in body
                continue

            # Handle string format: "separator", "same-line"
            tree_like = self._data_bag._main_data_tree
            data_path = self._data_bag._main_data_path
            if isinstance(item, str):
                widget_name = item
                params = None
                child_path = data_path
            # Handle dict format: {"text": "label"} or {"data-id": "foo", "text": "label"}
            elif isinstance(item, dict):
                # Extract data-tree if present (switches which tree is used as main)
                child_data_tree = item.get("data-tree")
                if child_data_tree:
                    tree_like = self._data_bag._data_trees.get(child_data_tree)
                    if not tree_like:
                        return Result.error(f"Composite: unknown data-tree '{child_data_tree}'")
                    data_path = DataPath("/")  # Start at root of the new tree

                # Extract data-id if present (navigates within the tree)
                child_data_id = item.get("data-id")
                if child_data_id is None:
                    child_path = data_path
                else:
                    child_path = data_path / child_data_id

                # Extract widget name and params (excluding data-id and data-tree)
                widget_keys = [k for k in item.keys() if k not in ("data-id", "data-tree")]
                if len(widget_keys) != 1:
                    return Result.error(f"Composite template item must have one widget key (plus optional data-id/data-tree), got {len(widget_keys)}: {widget_keys}")

                widget_name = widget_keys[0]
                params = item[widget_name]
            else:
                return Result.error(f"Composite template item must be str or dict, got {type(item)}")

            # Prepend namespace if widget_name doesn't have one
            # Factory is smart enough to fallback to primitives if needed
            if '.' not in widget_name and self._namespace:
                full_widget_name = f"{self._namespace}.{widget_name}"
            else:
                full_widget_name = widget_name

            # Create single child widget via factory
            res = self._factory.create_widget(full_widget_name, tree_like, child_path, params, self._data_bag._data_trees)
            if not res:
                return Result.error(f"Composite: failed to create child widget '{widget_name}'", res)

            child = res.unwrapped

            # Popup cannot be a child of Composite - must be standalone
            if child.__class__.__name__ == "Popup":
                return Result.error(f"Popup '{widget_name}' cannot be child of Composite. Popup must be used standalone (root element or event show)")

            # Child is already initialized by factory.create_widget (via Object.create)
            self._children.append(child)

        return Ok(None)

    def render(self) -> Result[None]:
        """Render all children - Composite doesn't use head/body pattern"""
        if self._children is None:
            res = self._init_children()
            if not res:
                return Result.error(f"Composite: _init_children failed", res)

        # Push styles before rendering children
        res = self._push_styles()
        if not res:
            self._handle_error(Result.error("Composite: _push_styles failed", res))

        for child in self._children:
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
        for child in self._children:
            res = child.dispose()
            if not res:
                return Result.error(f"Composite: child dispose failed", res)
        return Ok(None)

