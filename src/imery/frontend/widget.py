"""
Widget - Base class and primitive widgets for imgui
Each widget gets DataBag for data access
"""

from imgui_bundle import imgui
from imery.frontend.types import Visual
from imery.backend.types import TreeLike
from imery.types import DataPath, Object, EventHandler
from imery.data_bag import DataBag
from imery.dispatcher import Dispatcher
from imery.result import Result, Ok

from typing import Optional, Dict, Any, Union




EVENT_COMMAND_NAMES = {"show", "add-data-child", "dispatch-event", "default", "close", "set-data-value"}

def _render_error_simple(error) -> Result[None]:
    """Display errors using bullet points recursively - fallback method"""
    print("_render_error_simple", error)
    def render_tree(obj, depth=0):
        """Recursively render tree structure with bullets"""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    imgui.bullet_text(f"{key}:")
                    imgui.indent()
                    render_tree(value, depth + 1)
                    imgui.unindent()
                else:
                    imgui.bullet_text(f"{key}: {value}")
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, (dict, list)):
                    imgui.bullet_text(f"[{i}]:")
                    imgui.indent()
                    render_tree(item, depth + 1)
                    imgui.unindent()
                else:
                    imgui.bullet_text(f"[{i}]: {item}")
        else:
            imgui.bullet_text(str(obj))

    imgui.text_colored(imgui.ImVec4(1.0, 0.0, 0.0, 1.0), "Errors:")
    imgui.separator()
    render_tree(error)
    print("_render_error_simple")
    return Ok(None)

class Widget(Visual, EventHandler):
    """Base class for all widgets"""

    def __init__(self, factory: "WidgetFactory", dispatcher: Dispatcher, namespace: str, data_bag: DataBag):
        """
        Args:
            factory: WidgetFactory for creating nested widgets
            dispatcher: Event dispatcher
            namespace: Current namespace (e.g., "demo_widgets")
            data_bag: DataBag instance for data access
        """
        super().__init__()
        self._factory = factory
        self._dispatcher = dispatcher
        self._namespace = namespace
        self._data_bag = data_bag
        self._style_color_count = 0
        self._style_var_count = 0
        self._event_handlers = {}  # event_name -> list of command specs (lazy evaluated)
        self._body = None  # Body widget created from activated event
        self._is_body_activated = False
        self._should_create_body = False
        self._is_open = True
        self._last_error = None
        self._render_cycle = -1
        self._clicked = False

        # we collect errors from different step! there should be only one main error collected
        self._error_widget = None
        self._errors = []

        self._styles_pushed = False
        self._dispatch_handlers = []  # List of on-dispatch handler specs


    def init(self) -> Result[None]:
        """Initialize widget - override in subclasses if needed"""
        res = self._data_bag.init()
        if not res:
            return Result.error("Widget: failed to init DataBag", res)
        res = self._init_events()
        if not res:
            return Result.error("Widget: failed to initialize events", res)

        return Ok(None)

    @property
    def is_open(self):
        return self._is_open

    @property
    def is_empty(self) -> bool:
        """Check if widget has no content - override in subclasses"""
        return True

    @property
    def body(self) -> Result[None]:
        if not self._body:
            res = self._ensure_body()
            if not res:
                Result.error("Widget: body: could not create body")

    def _init_events(self) -> Result[None]:
        """Parse and store event specifications from event-handlers section"""
        # Get event-handlers section
        res = self._data_bag.get_static("event-handlers", {})
        if not res:
            return Result.error("Widget: _init_events: failed to get event-handlers", res)
        event_handlers = res.unwrapped

        # List of supported event names (except on-dispatch which is handled separately)
        event_names = ["on-active", "on-click", "on-double-click", "on-right-click", "on-hover", "on-error"]

        # Check each event in event-handlers
        for event_name in event_names:
            event_spec = event_handlers.get(event_name)
            if event_spec is not None:
                res = self._normalize_event_spec(event_name, event_spec)
                if not res:
                    return Result.error("Widget: _init_events: Could not init events", res)
                self._event_handlers[event_name] = res.unwrapped

        # Handle on-dispatch separately - register with dispatcher
        on_dispatch = event_handlers.get("on-dispatch")
        if on_dispatch:
            print(f"_init_events: on_dispatch={on_dispatch}")
            if not isinstance(on_dispatch, list):
                on_dispatch = [on_dispatch]
            self._dispatch_handlers = on_dispatch
            # Register with dispatcher for each source/name pair
            for handler_spec in on_dispatch:
                if isinstance(handler_spec, dict):
                    source = handler_spec.get("source")
                    name = handler_spec.get("name")
                    if source and name:
                        key = f"{source}/{name}"
                        print(f"_init_events: registering handler for key={key}")
                        self._dispatcher.register_event_handler(key, self)

        return Ok(None)

    def _evaluate_condition(self, condition, metadata: dict) -> Ok(bool):
        """
        Evaluate a condition against metadata.

        Condition can be:
        - list → implicit AND (all conditions must be true)
        - dict with single field: value → metadata[field] == value
        - dict with "and": [conditions] → all must be true
        - dict with "or": [conditions] → at least one must be true
        - dict with "not": condition → negate the condition

        Args:
            condition: Condition specification (list or dict)
            metadata: Metadata dict to check against

        Returns:
            bool: True if condition passes, False otherwise
        """
        # List → implicit AND
        # print(f"Widget: _evaluate_condition: {condition}")
        if isinstance(condition, str):
            if not condition in ["always", "never"]:
                return Result.error(f"Widget: _evaluate_condition: Unknown 'when' condition specified '{condition}'")
            if condition == "always":
                return Ok(True)
            return Ok(False)

        if isinstance(condition, list): # default is and of all conditions
            out = True
            for cond in condition:
                res = self._evaluate_condition(c, metadata)
                if not res:
                    return Result.error(f"Widget: _evaluate_condition: Failed to evaluate condition for '{cond}'")
                out = out and res.unwrapped
            return Ok(out)

        if not isinstance(condition, dict):
            return Ok(False)

        # Check for logical operators
        if "and" in condition:
            conditions = condition["and"]
            if isinstance(conditions, list):
                return all(self._evaluate_condition(c, metadata) for c in conditions)
            # Single condition (collapsed list)
            return self._evaluate_condition(conditions, metadata)

        if "or" in condition:
            conditions = condition["or"]
            if isinstance(conditions, list):
                return any(self._evaluate_condition(c, metadata) for c in conditions)
            # Single condition (collapsed list)
            return self._evaluate_condition(conditions, metadata)

        if "not" in condition:
            inner_condition = condition["not"]
            res = self._evaluate_condition(inner_condition, metadata)
            if not res:
                return Result.error(f"Widget: _evaluate_condition: Failed to evaluate condition for 'not': '{inner_condition}'")
            return Ok(not self.unwrapped)

        # Simple field comparison: {field: expected_value}
        # Should have exactly one key
        if len(condition) == 1:
            field_name, expected_value = next(iter(condition.items()))
            actual_value = metadata.get(field_name)
            return Ok(actual_value == expected_value)

        # Multiple keys but no logical operator → invalid, return False
        return Ok(False)

    def _normalize_event_spec_item(self, event_name, event_spec: Union[str, dict]) -> Result[dict]:

        if isinstance(event_spec, str):
            return Ok({
                      "command": event_spec,
                      "when": "always",
                      "data": None})
        if isinstance(event_spec, dict):
            when = event_spec.get("when", "always")
            action = None 
            for action_name in EVENT_COMMAND_NAMES:
                if action_name in event_spec:
                    if action is None:
                        action = action_name
                    else:
                        Result.error(f"both '{action_name}' and '{action}' is specified for {event_name}")
            if action is None:
                return Result.error(f"no known action specified for event: {event_name}, {event_spec}")
            data = event_spec.get(action)
            return Ok({
                      "command": action,
                      "when": when,
                      "data": data})

        return Result.error(f"Widget: _normalize_event_spec_item: unexpected type: {type(event_spec)}:, {event_spec}")



    def _normalize_event_spec(self, event_name: str, event_spec: Union[str, dict, list]) -> Result[list]:
        """
        Normalize event specification into a list of commands.

        Event spec can be:
        - string "default" → [{"command": "default"}]
        - string (other) → [{"command": "show", "what": string}]
        - dict with action keys (show/dispatch) → [{"command": "show"/"dispatch", ...}]
        - dict (other) → [{"command": "show", "what": dict}] (widget spec)
        - list → normalize each item

The event spec may have following layouts
action is the body (value) of the event. The body may be a string, a dict or a list of them
widgets:
    type: popup
    body:
    - menu-item:
        label: "add layer"
        on-click: default
or
widgets:
    type: popup
    body:
    - menu-item:
        label: "add layer"
        on-click:
            when: always
            add-data-child:
                name: "layer-new"
                metadata:
                    label: "new layer"
or
widgets:
    type: popup
    body:
    - menu-item:
        label: "add layer"
        on-click:
            when: always
            add-data-child:
                name: "layer-new"
                metadata:
                    label: "new layer"

        Returns:
            list: List of command dicts, each with "action", "what"/"message", optional "when"
        """
        if event_spec is None:
            return Ok([])
        # List → normalize each item
        if isinstance(event_spec, str):
            res = self._normalize_event_spec_item(event_name, event_spec)
            if not res:
                return Result.error("Widget: _normalize_event_spec: For '{event_name}', failed to normalize item {event_spec}:" , res)
            return Ok([res.unwrapped])
            
        if isinstance(event_spec, dict):
            res = self._normalize_event_spec_item(event_name, event_spec)
            if not res:
                return Result.error("Widget: _normalize_event_spec: For '{event_name}', failed to normalize item {event_spec}:" , res)
            return Ok([res.unwrapped])

        if isinstance(event_spec, list):
            output = []
            for action in event_spec:
                res = self._normalize_event_spec_item(event_name, action)
                if not res:
                    return Result.error("Widget: _normalize_event_spec: For '{event_name}', failed to normalize item {action}:" , res)
                output.append(res.unwrapped)
            return Ok(output)

        return Result.error(f"unexpected data for event '{event_name}', spec '{type(event_spec)}' {event_spec}")

    
    def _execute_event_command_add_data_child(self, event_name: str, command: str, data: Optional[Union[str, dict, list]] = None) -> Result[None]:
        print("adding child to data")
        if not isinstance(data, dict):
            return Result.error(f"Widget: _execute_event_command_dispatch_event: expected dict, got '{type(data)}'")
        # Get child name and data from command spec
        child_name = data.get("name")
        if not child_name:
            return Result.error(f"Widget: _execute_event_command_add_data_child: missing 'name' parameter")

        # Get data - can be metadata dict or any other data
        child_data = data.get("metadata")
        if child_data is None:
            return Result.error(f"Widget: _execute_event_command_add_data_child: missing 'metadata' or 'data' parameter")

        # Get target path (optional data-id, supports ".." for parent)
        data_id = data.get("data-id")
        data_path = self._data_bag._main_data_path
        if data_id:
            target_path = data_path / data_id
        else:
            target_path = data_path

        # Call add_child through field_values
        res = self._data_bag.add_child(target_path, child_name, child_data)
        if not res:
            return Result.error(f"Widget: _execute_event_command_add_data_child: failed to add child '{child_name}' at '{target_path}'", res)
        return Ok(None)


    def _execute_event_command_show(self, event_name: str, command: str, data: Optional[Union[str, dict, list]] = None) -> Result[None]:
        res = self._create_widget_from_spec(data)
        if not res:
            return Result.error(f"Widget: _execute_event_command_show: failed to create widget from spec: {data}")
        widget = res.unwrapped
        res = widget.render()
        if not res:
            return Result.error(f"Widget: _execute_event_command_show: failed to render widget: {data}")
        return Ok(None)

    def _execute_event_command_default(self, event_name: str, command: str, data: Optional[Union[str, dict, list]] = None) -> Result[None]:
        """Default action: for click events, set selection to current data path"""
        if event_name == "on-click":
            # Set selection to current data path
            # If static has "selection" reference, it writes there
            res = self._data_bag.get_data_path_str()
            if not res:
                return Result.error("default action: failed to get data path", res)
            res = self._data_bag.set("selection", res.unwrapped)
            if not res:
                return Result.error("default action: failed to set selection", res)
        return Ok(None)


    def _execute_event_command_dispatch_event(self, event_name: str, command: str, data: Optional[Union[str, dict, list]] = None) -> Result[None]:
        """Dispatch an event with source=widget id, name=data (event name)"""
        print(f"dispatch-event: data={data}")
        # Get widget id
        res = self._data_bag.get_static("id")
        if not res:
            return Result.error("dispatch-event: failed to get widget id", res)
        widget_id = res.unwrapped
        print(f"dispatch-event: widget_id={widget_id}")
        if not widget_id:
            return Result.error("dispatch-event: widget must have 'id' to dispatch events")

        # data is the event name (string)
        if not isinstance(data, str):
            return Result.error(f"dispatch-event: event name must be a string, got {type(data)}")

        event = {
            "source": widget_id,
            "name": data
        }
        print(f"dispatch-event: dispatching {event}")
        return self._dispatcher.dispatch_event(event)

    def _resolve_action_references(self, value: Any) -> Result[Any]:
        """
        Recursively resolve @ references in action parameters.
        Handles strings, dicts, and lists.
        """
        if isinstance(value, str):
            if '@' in value:
                return self._data_bag._resolve_reference(value)
            return Ok(value)
        elif isinstance(value, dict):
            resolved = {}
            for k, v in value.items():
                res = self._resolve_action_references(v)
                if not res:
                    return Result.error(f"Failed to resolve reference in '{k}'", res)
                resolved[k] = res.unwrapped
            return Ok(resolved)
        elif isinstance(value, list):
            resolved = []
            for item in value:
                res = self._resolve_action_references(item)
                if not res:
                    return Result.error("Failed to resolve reference in list item", res)
                resolved.append(res.unwrapped)
            return Ok(resolved)
        else:
            return Ok(value)

    def _execute_event_command_add_data_child(self, event_name: str, command: str, data: Optional[Union[str, dict, list]] = None) -> Result[None]:
        """Handle add-data-child action - adds a new child node to the data tree."""
        print(f"add-data-child: data={data}")
        if not isinstance(data, dict):
            return Result.error(f"add-data-child: expected dict, got '{type(data)}'")

        res = self._data_bag.add_child(data)
        if not res:
            print(f"add-data-child: FAILED: {res}")
            return Result.error("add-data-child: failed", res)

        print(f"add-data-child: SUCCESS")
        return Ok(None)

    def _execute_event_command_close(self, event_name: str, command: str, data: Optional[Union[str, dict, list]] = None) -> Result[None]:
        """Close action - closes the current popup context."""
        print("closing widget")
        return self.close()

    def close(self) -> Result[None]:
        """Close the widget. Override in subclasses (e.g., Popup)."""
        return Ok(None)

    def _execute_event_command_set_data_value(self, event_name: str, command: str, data: Optional[Union[str, dict, list]] = None) -> Result[None]:
        """
        Set a value in the data tree.
        data should have 'target' (path reference) and 'value' (value or reference).
        """
        if not isinstance(data, dict):
            return Result.error(f"set-data-value: expected dict, got '{type(data)}'")

        target = data.get("target")
        value = data.get("value")

        if target is None:
            return Result.error("set-data-value: missing 'target'")

        # Resolve the value reference if it's a reference
        if isinstance(value, str) and '@' in value:
            res = self._data_bag._resolve_reference(value)
            if not res:
                return Result.error(f"set-data-value: failed to resolve value '{value}'", res)
            resolved_value = res.unwrapped
        else:
            resolved_value = value

        # Target should be a reference like $local@channel or @path
        if isinstance(target, str) and '@' in target:
            from imery.data_bag import REF_PATTERN
            match = REF_PATTERN.match(target)
            if match:
                tree_name = match.group(1)  # $tree or None
                path_str = match.group(2)   # path after @

                # Determine tree
                if tree_name:
                    tree_key = tree_name[1:]  # Remove $ prefix
                    tree = self._data_bag._data_trees.get(tree_key) if self._data_bag._data_trees else None
                    if not tree:
                        return Result.error(f"set-data-value: unknown tree '{tree_key}'")
                    if not path_str.startswith('/'):
                        path_str = '/' + path_str
                else:
                    tree = self._data_bag._data_trees.get(self._data_bag._main_data_key)

                # Resolve path
                if path_str.startswith('/'):
                    full_path = DataPath(path_str)
                elif path_str.startswith('..'):
                    parts = path_str.split('/')
                    current = self._data_bag._main_data_path
                    for part in parts:
                        if part == '..':
                            current = current.parent
                        elif part:
                            current = current / part
                    full_path = current
                else:
                    full_path = self._data_bag._main_data_path / path_str

                res = tree.set(full_path, resolved_value)
                if not res:
                    return Result.error(f"set-data-value: failed at '{full_path}'", res)

                return Ok(None)

        return Result.error(f"set-data-value: target '{target}' is not a valid reference")


    def _execute_event_commands(self, event_name: str) -> Result[None]:
        if event_name not in self._event_handlers:
            return Ok(None)
        commands = self._event_handlers[event_name]
        for cmd_spec in commands:
            if not isinstance(cmd_spec, dict):
                return Result.error(f"_execute_event_commands: expected dict, got '{type(cmd_spec)}'")
            # Check condition if present
            if "when" in cmd_spec:
                condition = cmd_spec["when"]
                metadata_res = self._data_bag.get_metadata()
                metadata = metadata_res.unwrapped if metadata_res else None
                if metadata and not self._evaluate_condition(condition, metadata):
                    continue
            if "command" not in cmd_spec:
                return Result.error(f"_execute_event_commands: 'command' key missing in {cmd_spec}")
            command = cmd_spec['command']
            method_name = f"_execute_event_command_{command.replace('-', '_')}"
            method = getattr(self, method_name, None)
            if method is None:
                return Result.error(f"_execute_event_commands: unknown command '{command}'")
            res = method(event_name, command, cmd_spec.get("data"))
            if not res:
                return Result.error(f"_execute_event_commands: '{command}' failed", res)

        return Ok(None)


    def _execute_event_commands_old(self, event_name: str) -> Result[None]:
        """
        Execute commands for an event.

        For each command:
        - Check "when" condition (if present)
        - Execute action: "show" or "dispatch"
        - Lazy create widgets on first execution

        Args:
            event_name: Name of the event ("clicked", "hovered", etc.)

        Returns:
            Result[None]
        """
        if event_name not in self._event_handlers:
            return Ok(None)

        commands = self._event_handlers[event_name]

        for i, cmd_spec in enumerate(commands):
            if not isinstance(cmd_spec, dict):
                continue


            # Get action (normalized format: {"action": "show"/"dispatch"/"default", "what": ...})
            action = cmd_spec.get("action")
            if action == "show":
                widget_spec = cmd_spec.get("what")
            elif action == "dispatch":
                message = cmd_spec.get("message") or cmd_spec.get("what")
            elif action == "default":
                # Default action - no additional data needed
                pass
            else:
                return Result.error(f"Unknown action in {event_name} event: {cmd_spec}")

            # Execute action
            if action == "default":
                # Default action: for "click" events, set "selected" field
                if event_name == "on-click":
                    set_res = self._data_bag.set("selection", str(self._data_bag._main_data_path))
                    if not set_res:
                        return Result.error(f"default action failed to set selected", set_res)
                # For other events, default does nothing

            elif action == "show":
                if "widget-instance" not in cmd_spec:
                    # Lazy create widget
                    res = self._create_widget_from_spec(widget_spec)
                    if not res:
                        return Result.error(f"Widget: Failed to create widget for {event_name} event", res)
                    cmd_spec["widget-instance"] = res.unwrapped

                # Render the widget
                widget = cmd_spec["widget-instance"]
                res = widget.render()
                if not res:
                    return Result.error(f"Failed to render widget for {event_name} event", res)

            elif action == "dispatch":
                # Placeholder for dispatch
                # TODO: Implement dispatch to dispatcher
                pass

            elif action == "add-data-child":
                # Get child name and data from command spec
                child_name = cmd_spec.get("name")
                if not child_name:
                    return Result.error(f"add-data-child: missing 'name' parameter")

                # Get data - can be metadata dict or any other data
                child_data = cmd_spec.get("metadata") or cmd_spec.get("data")
                if child_data is None:
                    return Result.error(f"add-data-child: missing 'metadata' or 'data' parameter")

                # Get target path (optional data-id, supports ".." for parent)
                data_id = cmd_spec.get("data-id")
                data_path = self._data_bag._main_data_path
                if data_id:
                    target_path = data_path / data_id
                else:
                    target_path = data_path

                # Call add_child through field_values
                res = self._data_bag.add_child(target_path, child_name, child_data)
                if not res:
                    return Result.error(f"add-data-child: failed to add child '{child_name}' at '{target_path}'", res)

            elif action == "add-data-key-value":
                #TODO
                pass

        return Ok(None)


    def _create_widget_from_spec(self, widget_spec) -> Result["Widget"]:
        """
        Create a widget from a specification.

        Args:
            widget_spec: String (widget name), dict (inline widget), or list (composite)

        Returns:
            Result[Widget]: Created widget instance
        """
        # String → widget reference
        if isinstance(widget_spec, str):
            widget_name = widget_spec
            if '.' not in widget_name and self._namespace:
                full_widget_name = f"{self._namespace}.{widget_name}"
            else:
                full_widget_name = widget_spec
            res = self._data_bag.inherit()
            if not res:
                return Result.error(f"Widget: _create_widget_from_spec: failed to create child DataBag", res)
            return self._factory.create_widget_from_bag(full_widget_name, res.unwrapped)

        # Dict or list → composite - use factory to avoid circular import
        if isinstance(widget_spec, (dict, list)):
            params = {"type": "composite", "body": [widget_spec] if isinstance(widget_spec, dict) else widget_spec}
            full_widget_name = f"{self._namespace}.composite" if self._namespace else "composite"
            res = self._data_bag.inherit(None, params)
            if not res:
                return Result.error("Widget: _create_widget_from_spec: failed to create child DataBag", res)
            res = self._factory.create_widget_from_bag(full_widget_name, res.unwrapped)
            if not res:
                return Result.error("Widget: _create_widget_from_spec: could not create widget", res)
            return Ok(res.unwrapped)

        return Result.error(f"Invalid widget spec type: {type(widget_spec)}")

    def _prepare_render(self) -> Result[None]:
        """Prepare for rendering - metadata is now accessed through DataBag"""
        return Ok(None)

    def _apply_style_dict(self, style_dict: dict) -> Result[None]:
        """Apply a single style dictionary (colors and vars)"""
        for style_name, style_value in style_dict.items():
            # Convert hyphenated name to underscore for enum lookup
            enum_name = style_name.replace("-", "_")

            # Try to find it as a color first
            try:
                color_enum = getattr(imgui.Col_, enum_name)
                # Convert list to ImVec4 if needed
                if isinstance(style_value, list):
                    if len(style_value) == 4:
                        color = imgui.ImVec4(style_value[0], style_value[1], style_value[2], style_value[3])
                    else:
                        return Result.error(f"Style color '{style_name}' requires 4 components, got {len(style_value)}")
                else:
                    return Result.error(f"Style color '{style_name}' must be a list")

                imgui.push_style_color(color_enum, color)
                self._style_color_count += 1
                continue
            except AttributeError:
                pass  # Not a color, try style var

            # Try to find it as a style var
            try:
                var_enum = getattr(imgui.StyleVar_, enum_name)
                # Convert list to ImVec2 if needed, otherwise use scalar
                if isinstance(style_value, list):
                    if len(style_value) == 2:
                        vec = imgui.ImVec2(style_value[0], style_value[1])
                        imgui.push_style_var(var_enum, vec)
                    else:
                        return Result.error(f"Style var '{style_name}' requires 1 or 2 components, got {len(style_value)}")
                else:
                    # Scalar value
                    imgui.push_style_var(var_enum, float(style_value))

                self._style_var_count += 1
                continue
            except AttributeError:
                return Result.error(f"Unknown style attribute '{style_name}'")

        return Ok(None)

    def _push_styles(self) -> Result[None]:
        """Push styles before rendering"""
        # Apply default style first
        res = self._data_bag.get_static("style")
        if not res:
            return Result.error("_push_styles: failed to get style", res)
        style = res.unwrapped
        if style and isinstance(style, dict):
            res = self._apply_style_dict(style)
            if not res:
                return Result.error("_push_styles: failed to apply default style", res)

        # Apply style-mapping based on metadata conditions
        res = self._data_bag.get_static("style-mapping")
        if not res:
            return Result.error("_push_styles: failed to get style-mapping", res)
        style_mapping = res.unwrapped
        metadata_res = self._data_bag.get_metadata()
        metadata = metadata_res.unwrapped if metadata_res else None
        if style_mapping and metadata:
            # style-mapping can be:
            # 1. Dict (old format): {field_name: style_dict, ...} - backward compatible
            # 2. List (new format): [{when: condition, style: style_dict}, ...]

            if isinstance(style_mapping, dict):
                # Old format: dict keys are field names to check
                for field_name, field_style in style_mapping.items():
                    # Simple field name - check if exists and truthy
                    condition = {field_name: True}

                    # Evaluate condition
                    if self._evaluate_condition(condition, metadata):
                        # Apply the style for this condition
                        if isinstance(field_style, dict):
                            res = self._apply_style_dict(field_style)
                            if not res:
                                return Result.error(f"_push_styles: failed to apply style-mapping for '{field_name}'", res)

            elif isinstance(style_mapping, list):
                # New format: list of {when: condition, style: style_dict}
                for mapping_entry in style_mapping:
                    if not isinstance(mapping_entry, dict):
                        continue

                    condition = mapping_entry.get("when")
                    entry_style = mapping_entry.get("style")

                    if condition is None or entry_style is None:
                        continue

                    # Evaluate condition
                    if self._evaluate_condition(condition, metadata):
                        # Apply the style
                        if isinstance(entry_style, dict):
                            res = self._apply_style_dict(entry_style)
                            if not res:
                                return Result.error(f"_push_styles: failed to apply style-mapping for condition", res)

        self._styles_pushed = True
        return Ok(None)

    def _pop_styles(self) -> Result[None]:
        """Pop styles after rendering - called by subclasses"""
        if not self._styles_pushed:
            return Ok(True)
        if self._style_color_count > 0:
            imgui.pop_style_color(self._style_color_count)
            self._style_color_count = 0

        if self._style_var_count > 0:
            imgui.pop_style_var(self._style_var_count)
            self._style_var_count = 0

        self._styles_pushed = False
        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        """Render widget core - must be implemented by subclasses
        """
        return Result.error("Widget: _pre_render_head() not implemented")

    def _post_render_head(self) -> Result[None]:
        """Widget-specific post-render cleanup - override in subclasses if needed

        Examples:
            TreeNode: imgui.tree_pop() if widget was opened
            Menu: imgui.end_menu() if widget was opened
            Indent: imgui.unindent() always
        """
        return Ok(None)

    def _ensure_body(self) -> Result[None]:
        if self._body is not None:
            return Ok(None)
        res = self._data_bag.get_static("body")
        if not res:
            return Result.error("_ensure_body: failed to get body", res)
        body_spec = res.unwrapped
        if body_spec is not None:
            res = self._create_widget_from_spec(body_spec)
            if not res:
                return Result.error("_ensure_body: failed to create body widget", res)
            self._body = res.unwrapped
        return Ok(None)


    def _render_errors(self) -> Result[None]:
        """Display all collected errors as a tree view"""
        if len(self._errors) == 0:
            return Ok(None)

        errors_tree = Result.error("Error:", self._errors).as_tree
        import pprint
        pprint.pp(errors_tree)
        # Create error widget only once (persist across render cycles)
        if self._error_widget is None:
            print("Widget: _render_errors: creating error widget")
            errors_tree = Result.error("Error:", self._errors).as_tree


            from imery.backend.simple_data_tree import SimpleDataTree
            # Convert errors list to tree structure
            res = SimpleDataTree.create(errors_tree)
            if not res:
                errors = self._errors.copy()
                errors.append(res)
                return _render_error_simple(Result.error("Widget: _render_errors: failed to create SimpleDataTree from errors", errors).as_tree)

            error_tree = res.unwrapped
            res = self._factory.create_widget("builtin.error-tree-view", error_tree, DataPath("/"))
            if not res:
                errors = self._errors.copy()
                errors.append(res)
                return _render_error_simple(Result.error("Widget: _render_errors: failed to create 'tree-view' for errors", errors).as_tree)

            self._error_widget = res.unwrapped

        # Render the persisted error widget every frame
        res = self._error_widget.render()
        if not res:
            errors = self._errors.copy()
            errors.append(res)
            return _render_error_simple(Result.error("Widget: _render_errors: failed to render 'tree-view' for errors", errors).as_tree)

        return Ok(None)

    def _handle_error(self, error) -> Result[Any]:
        if not error:
            self._errors.append(error)
        return error

    def render(self) -> Result[None]:
        """Unified render flow for all widgets"""
        # Prepare: load metadata and label
        # print("Widget: render 000", self)

        self._render_cycle = self._render_cycle + 1
        res = self._prepare_render()
        if not res:
            self._handle_error(Result.error("Widget: render: prepare_render failed", res))

        # Push styles
        if not self._errors:
            res = self._push_styles()
            if not res:
                self._handle_error(Result.error("Widget: render: _push_styles failed", res))

        # print("Widget: render 010", self)
        # First Render the "head", in case of Button, the button is itself the head
        # and the widget activated is the body, even if rendered in the "same window" or in popup or modal
        if not self._errors:
            res = self._pre_render_head()
            if not res:
                self._handle_error(Result.error(f"Widget: render: _pre_render_head failed for class: {str(type(self))}", res))

        if not self._errors:
            res = self._detect_and_execute_events()
            if not res:
                self._handle_error(Result.error("Widget: render: detect_and_execute_events failed", res))

        if not self._errors:
            if self._body is None and (self._is_body_activated or self._should_create_body):
                res = self._ensure_body()
                if not res:
                    self._handle_error(Result.error("render: ensure_body failed", res))

        # print("Widget: render 1", self)
        # print("Widget: render 020", self)

        if not self._errors and self._is_body_activated:
            if self._body:
                res = self._body.render()
                if not res:
                    self._handle_error(Result.error("Widget: render: body.render failed", res))

        # Widget-specific post-render (cleanup like tree_pop, end_menu, etc.)
        # Must be called whenever body is activated, even if body widget doesn't exist yet
        res = self._post_render_head()
        if not res:
            self._handle_error(Result.error("Widget: render: _post_render_head failed", res))


        # Pop styles - always try to clean up
        res = self._pop_styles()
        if not res:
            self._handle_error(Result.error("render: _pop_styles failed", res))

        if self._body and not self._body.is_open:
            # This is mainly used for the Button-Popup logic
            self._is_body_activated = False
            self._body = None

        return self._render_errors()


    def _detect_and_execute_events(self) -> Result[None]:
        """Detect ImGui events and execute corresponding event handlers"""
        # activated event - triggered by widget return value
        if self._is_body_activated and "on-active" in self._event_handlers:
            res = self._execute_event_commands("on-active")
            if not res:
                return Result.error("Failed to execute activated event", res)

        # clicked event - left mouse button
        # TODO ... each widget should implement the manipulation of the self._clicked!
        # likely only tree-node reacts on is_item_clicked
        if (imgui.is_item_clicked(0)) and "on-click" in self._event_handlers:
            print("item clicked")
            res = self._execute_event_commands("on-click")
            if not res:
                return Result.error("Failed to execute 'on-click' commands", res)

        # right-clicked event - right mouse button
        if imgui.is_item_clicked(1) and "on-right-click" in self._event_handlers:
            res = self._execute_event_commands("on-right-click")
            if not res:
                return Result.error("Failed to execute 'on-right-click' commands", res)

        # double-clicked event
        if imgui.is_item_hovered() and imgui.is_mouse_double_clicked(0) and "on-double-click" in self._event_handlers:
            res = self._execute_event_commands("on-double-click")
            if not res:
                return Result.error("Failed to execute 'on-double-click' commands", res)

        # hovered event
        if imgui.is_item_hovered() and "on-hover" in self._event_handlers:
            res = self._execute_event_commands("on-hover")
            if not res:
                return Result.error("Failed to execute 'on-hover' commands", res)

        # automatic tooltip from head param
        if imgui.is_item_hovered():
            tooltip_res = self._data_bag.get("tooltip")
            if tooltip_res and tooltip_res.unwrapped:
                imgui.begin_tooltip()
                imgui.text(str(tooltip_res.unwrapped))
                imgui.end_tooltip()

        # hovered event
        if not self._last_error is None and "on-error" in self._event_handlers:
            res = self._execute_event_commands("on-error")
            if not res:
                return Result.error("Failed to execute 'on-error' commands", res)

        return Ok(None)

    def dispose(self) -> Result[None]:
        """Cleanup widget resources"""
        return Ok(None)
    
    def _close(self) -> Result[None]:
        return Result.error("Widget: _close: Not implemented")

    def handle_event(self, event: dict) -> Result[None]:
        """Handle dispatched events - called by dispatcher when event matches registered source/name"""
        print(f"handle_event: event={event}, dispatch_handlers={self._dispatch_handlers}")
        source = event.get("source")
        name = event.get("name")

        # Find matching handler in _dispatch_handlers
        for handler_spec in self._dispatch_handlers:
            if not isinstance(handler_spec, dict):
                continue
            if handler_spec.get("source") == source and handler_spec.get("name") == name:
                # Found match - execute "do" actions
                do_actions = handler_spec.get("do")
                if do_actions:
                    # Normalize to list
                    if not isinstance(do_actions, list):
                        do_actions = [do_actions]
                    # Execute each action
                    for action_spec in do_actions:
                        res = self._normalize_event_spec_item("on-dispatch", action_spec)
                        if not res:
                            return Result.error("handle_event: failed to normalize action", res)
                        cmd_spec = res.unwrapped
                        command = cmd_spec.get("command")
                        method_name = f"_execute_event_command_{command.replace('-', '_')}"
                        method = getattr(self, method_name, None)
                        if method is None:
                            return Result.error(f"handle_event: unknown command '{command}'")
                        res = method("on-dispatch", command, cmd_spec.get("data"))
                        if not res:
                            return Result.error(f"handle_event: '{command}' failed", res)
        return Ok(None)
