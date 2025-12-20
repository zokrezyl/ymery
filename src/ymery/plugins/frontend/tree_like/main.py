"""
Widget subclasses - primitive widgets for imgui
"""

import math
from imgui_bundle import imgui
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok

import pprint

@widget
class Button(Widget):
    """Button widget - uses generic event system for clicks"""

    def _pre_render_head(self) -> Result[None]:
        """Render button core - returns True if clicked"""
        label_res = self._data_bag.get("label")
        if not label_res:
            return Result.error("Button: failed to get label", label_res)
        label = label_res.unwrapped

        clicked = imgui.button(f"{label}###{self.uid}")
        if clicked:
            self._is_body_activated = True

        return Ok(None)



@widget
class Child(Widget):
    """Child window widget"""

    def _pre_render_head(self) -> Result[None]:
        """Begin child window"""
        label_res = self._data_bag.get("label", self.uid)
        if isinstance(label_res, Result):
            if not label_res:
                return Result.error("Child: failed to get label", label_res)
            label = label_res.unwrapped
        else:
            label = label_res

        # Get params
        size = [0, 0]
        res = self._handle_error(self._data_bag.get("size", size))
        if res:
            size = res.unwrapped

        border = False
        res = self._handle_error(self._data_bag.get("border", border))
        if res:
            border = res.unwrapped

        flags = imgui.ChildFlags_.none
        flags_list = []
        res = self._handle_error(self._data_bag.get("flags", flags_list))
        if res:
            flags_list = res.unwrapped
        for flag_name in flags_list:
            flag_attr = flag_name.replace("-", "_")
            if hasattr(imgui.ChildFlags_, flag_attr):
                flags |= getattr(imgui.ChildFlags_, flag_attr)

        child_opened = imgui.begin_child(f"{label}###{self.uid}", size, border, flags)
        self._is_body_activated = child_opened
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End child window"""
        imgui.end_child()
        return Ok(None)


@widget
class Columns(Widget):
    """Columns layout widget"""

    def _pre_render_head(self) -> Result[None]:
        """Begin columns"""
        count = 1
        res = self._handle_error(self._data_bag.get("count", count))
        if res:
            count = res.unwrapped

        label = self.uid
        res = self._handle_error(self._data_bag.get("id", label))
        if res:
            label = res.unwrapped

        border = True
        res = self._handle_error(self._data_bag.get("border", border))
        if res:
            border = res.unwrapped

        imgui.columns(count, label, border)
        self._is_body_activated = True
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End columns"""
        imgui.columns(1)
        return Ok(None)


@widget
class NextColumn(Widget):
    """Next column widget"""

    def _prepare_render(self) -> Result[None]:
        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        """Move to next column"""
        imgui.next_column()
        return Ok(None)


@widget
class Group(Widget):
    """Group widget"""

    def _pre_render_head(self) -> Result[None]:
        """Begin group"""
        imgui.begin_group()
        self._is_body_activated = True
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End group"""
        imgui.end_group()
        return Ok(None)


@widget
class Tooltip(Widget):
    """Tooltip widget - uses activated event for content, like TreeLike widgets"""

    def _pre_render_head(self) -> Result[None]:
        """Render tooltip - always returns True to trigger activated event"""
        tooltip_opened = imgui.begin_tooltip()
        if self._render_cycle == 0:
            # workarround for Popup as in first render cycle it returns always 0
            self._is_open = True
            self._is_body_activated = True
        else:
            self._is_open = tooltip_opened
            self._is_body_activated = tooltip_opened
        return Ok(None)  # Always "open" to show content via activated event

    def _post_render_head(self) -> Result[None]:
        """End tooltip after rendering activated content"""
        imgui.end_tooltip()
        return Ok(None)

    def dispose(self) -> Result[None]:
        return Ok(None)


@widget
class TreeNode(Widget):
    """Tree node widget - renders collapsible tree structure"""

    def _pre_render_head(self) -> Result[None]:
        """Render tree node core"""

        if self._render_cycle == 0:
            # on the first cycle we set the body as activated to solve the chicken-egg dependency between
            # creating the body widget and "if should create"
            # we cannot create first the body widget as for button-popup flow the popup needs to be created after
            # the button event. The button is detecting the popup creation if pre_render_head is setting the body_activated to true
            self._should_create_body = True
            return Ok(None)

        label_res = self._data_bag.get("label")
        if not label_res:
            return Result.error("TreeNode: failed to get label", label_res)
        label = label_res.unwrapped

        imgui_id = f"{label}###{self.uid}"

        # Check if body exists and is not empty
        has_body = False
        if self._body is not None:
            is_empty_res = self._body.is_empty
            if is_empty_res:
                has_body = not is_empty_res.unwrapped

        if has_body:
            # Has body - render as expandable
            self._is_body_activated = imgui.tree_node(imgui_id)
        else:
            # No body - render as leaf (no arrow), never open
            imgui.tree_node_ex(imgui_id, imgui.TreeNodeFlags_.leaf | imgui.TreeNodeFlags_.no_tree_push_on_open)
            self._is_body_activated = False  # Leaf nodes are never "opened"

        return Ok(None)

    
    def _post_render_head(self) -> Result[None]:
        """Pop tree node after rendering - only if has body"""
        if self._is_body_activated:
            imgui.tree_pop()
        return Ok(None)


@widget
class CollapsingHeader(Widget):
    """Collapsing header widget - similar to tree node but different visual style"""

    def _pre_render_head(self) -> Result[None]:
        """Render collapsing header core"""
        label_res = self._data_bag.get("label")
        if not label_res:
            return Result.error("CollapsingHeader: failed to get label", label_res)
        label = label_res.unwrapped

        imgui_id = f"{label}###{self.uid}"
        self._is_body_activated = imgui.collapsing_header(imgui_id)
        return Ok(None)



@widget
class Indent(Widget):
    """Indent widget - indents body content"""

    def _pre_render_head(self) -> Result[None]:
        """Render indent - always opens to render body"""

        res = self._data_bag.get("width", 0.0)
        if not res:
            return Result.error("Indent: failed to get 'width'", res)
        width = res.unwrapped
        if width != 0.0:
            imgui.indent(width)
        else:
            imgui.indent()
        self._is_body_activated = True
        return Ok(None)  


    def _post_render_head(self) -> Result[None]:
        """Unindent after rendering"""
        res = self._data_bag.get("width", 0.0)
        if not res:
            return Result.error("Indent: failed to get 'width'", res)
        width = res.unwrapped
        if width != 0.0:
            imgui.unindent(width)
        else:
            imgui.unindent()
        return Ok(None)


@widget
class MenuBar(Widget):
    """Menu bar widget - container for menus (requires ImGuiWindowFlags_MenuBar on parent window)"""

    def _pre_render_head(self) -> Result[None]:
        """Render menu bar core"""
        self._is_body_activated = imgui.begin_menu_bar()
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End menu bar after rendering"""
        if self._is_body_activated:
            imgui.end_menu_bar()
        return Ok(None)


@widget
class MainMenuBar(Widget):
    """Main menu bar widget - creates menu bar at top of screen"""

    def _pre_render_head(self) -> Result[None]:
        """Render main menu bar core"""
        self._is_body_activated = imgui.begin_main_menu_bar()
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End main menu bar after rendering"""
        if self._is_body_activated:
            imgui.end_main_menu_bar()
        return Ok(None)


@widget
class Menu(Widget):
    """Menu widget - wraps content in imgui menu"""

    def _pre_render_head(self) -> Result[None]:
        """Render menu core"""
        res = self._data_bag.get("label", "NO-LABEL")
        if not res:
            return Result.error("Menu: failed to get 'label'", res)
        label = res.unwrapped
        res = self._data_bag.get("enabled", True)
        if not res:
            return Result.error("Menu: failed to get 'enabled'", res)
        enabled = res.unwrapped

        self._is_body_activated = imgui.begin_menu(label, enabled)
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End menu after rendering"""
        if self._is_body_activated:
            imgui.end_menu()
        return Ok(None)


@widget
class MenuItem(Widget):
    """Menu item widget - clickable menu entry"""

    def _pre_render_head(self) -> Result[None]:
        """Render menu item - returns True if clicked"""

        #pprint.pp(self._data_bag.as_tree)
        #pprint.pp(self._data_bag.get_metadata())

        res = self._data_bag.get("label")
        if not res:
            return Result.error("MenuItem: failed to get 'label'", res)
        label = res.unwrapped

        res = self._data_bag.get("shortcut", "")
        if not res:
            return Result.error("MenuItem: could not get 'shortcut'", res)
        shortcut = res.unwrapped

        res = self._data_bag.get("selection", False)
        if not res:
            return Result.error("MenuItem: could not get 'selection'", res)
        selection = res.unwrapped

        res = self._data_bag.get("enabled", True)
        if not res:
            return Result.error("MenuItem: could not get 'enabled'", res)
        enabled = res.unwrapped

        clicked, _ = imgui.menu_item(label, shortcut, selection, enabled)

        self._is_body_activated = clicked
        self._clicked = False

        return Ok(None)  # Return True if clicked (can render body)


@widget
class TabBar(Widget):
    """Tab bar widget - container for tab items"""

    def _pre_render_head(self) -> Result[None]:
        """Render tab bar core"""
        res = self._data_bag.get("label", "TabBar")
        if not res:
            return Result.error("TabBar: failed to get 'label'", res)
        label = res.unwrapped

        imgui_id = f"{label}###{self.uid}"
        self._is_body_activated = imgui.begin_tab_bar(imgui_id)
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End tab bar after rendering"""
        if self._is_body_activated:
            imgui.end_tab_bar()
        return Ok(None)


@widget
class TabItem(Widget):
    """Tab item widget - individual tab within a tab bar"""

    def _pre_render_head(self) -> Result[None]:
        """Render tab item core"""
        res = self._data_bag.get("label")
        if not res:
            return Result.error("TabItem: failed to get 'label'", res)
        label = res.unwrapped

        imgui_id = f"{label}###{self.uid}"
        self._is_body_activated = imgui.begin_tab_item(imgui_id)[0]
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End tab item after rendering"""
        if self._is_body_activated:
            imgui.end_tab_item()
        return Ok(None)


@widget
class ColorEdit(Widget):
    """Color edit widget - RGBA color picker"""

    def _pre_render_head(self) -> Result[None]:
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"ColorEdit: failed to get value", value_res)
        value = value_res.unwrapped

        # Value should be list of 4 floats [r, g, b, a]
        if isinstance(value, str):
            # Try to parse string as list
            try:
                import ast
                value = ast.literal_eval(value)
            except:
                value = [1.0, 1.0, 1.0, 1.0]  # Default white

        if not isinstance(value, list) or len(value) != 4:
            value = [1.0, 1.0, 1.0, 1.0]  # Default white

        imgui_id = f"###{self.uid}"

        changed, new_color = imgui.color_edit4(imgui_id, value)
        if changed:
            # Convert to list for storage
            color_list = [new_color[0], new_color[1], new_color[2], new_color[3]]
            set_res = self._data_bag.set("label", color_list)
            if not set_res:
                return Result.error(f"ColorEdit: failed to set value", set_res)

        return Ok(None)


@widget
class ColorButton(Widget):
    """Color button widget - displays a color as a clickable button"""

    def _pre_render_head(self) -> Result[None]:
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"ColorButton: failed to get value", value_res)
        value = value_res.unwrapped

        # Value should be list of 4 floats [r, g, b, a]
        if isinstance(value, str):
            # Try to parse string as list
            try:
                import ast
                value = ast.literal_eval(value)
            except:
                value = [1.0, 1.0, 1.0, 1.0]  # Default white

        if not isinstance(value, list) or len(value) != 4:
            value = [1.0, 1.0, 1.0, 1.0]  # Default white

        # Convert to ImVec4
        color = imgui.ImVec4(value[0], value[1], value[2], value[3])

        imgui_id = f"###{self.uid}"

        clicked = imgui.color_button(imgui_id, color)
        if clicked:
            self._is_body_activated = True

        return Ok(None)


@widget
class Draggable(Widget):
    """Draggable container widget - renders body at draggable absolute screen position.

    Body widgets (buttons, etc.) handle their own clicks normally.
    Dragging is detected separately when mouse drags in our area.

    Parameters:
        size: Size of draggable area [width, height] (default: [30, 30])
        position: Initial position offset [x, y] from parent widget (default: [5, -35])
        bounds: Movement bounds. Options:
            - omitted or "auto": constrain to available content region (default)
            - "window": constrain to full window/viewport
            - [min_x, min_y, max_x, max_y]: relative to cursor position
            - {absolute: [min_x, min_y, max_x, max_y]}: screen coordinates
    """

    def init(self) -> Result[None]:
        self._position = None  # (x, y) offset, initialized on first render
        self._drag_active = False
        self._widget_pos = None
        self._size = None
        self._bounds = None
        self._cursor_screen_pos = None
        self._saved_cursor_pos = None
        self._offset = None
        return super().init()

    def _pre_render_head(self) -> Result[None]:
        """Position body at draggable location - body handles its own clicks"""
        # Get size
        res = self._data_bag.get("size", [30, 30])
        if not res:
            return Result.error("Draggable: failed to get size", res)
        size_list = res.unwrapped
        self._size = imgui.ImVec2(float(size_list[0]), float(size_list[1]))

        # Get initial position offset
        res = self._data_bag.get("position", [5, -35])
        if not res:
            return Result.error("Draggable: failed to get position", res)
        initial_offset = res.unwrapped

        # Get cursor screen position (reference point for relative positioning)
        cursor_screen_pos = imgui.get_cursor_screen_pos()
        self._cursor_screen_pos = cursor_screen_pos

        # Calculate bounds (as screen coordinates)
        res = self._data_bag.get("bounds", "auto")
        if not res:
            return Result.error("Draggable: failed to get bounds", res)
        bounds_param = res.unwrapped

        if bounds_param == "auto":
            # cursor_screen_pos is at BOTTOM of subplot (after plot renders)
            # cursor + content_avail = remaining area BELOW subplot
            # So subplot is ABOVE cursor, from content start to cursor
            window_pos = imgui.get_window_pos()
            window_size = imgui.get_window_size()
            cursor_start = imgui.get_cursor_start_pos()
            self._bounds = (
                window_pos.x,
                window_pos.y + cursor_start.y,
                window_pos.x + window_size.x - self._size.x,
                cursor_screen_pos.y - self._size.y
            )
        elif bounds_param == "window":
            # Full viewport/display bounds
            viewport = imgui.get_main_viewport()
            self._bounds = (
                viewport.pos.x,
                viewport.pos.y,
                viewport.pos.x + viewport.size.x - self._size.x,
                viewport.pos.y + viewport.size.y - self._size.y
            )
        elif isinstance(bounds_param, dict) and "absolute" in bounds_param:
            # Absolute screen coordinates
            abs_bounds = bounds_param["absolute"]
            self._bounds = (
                float(abs_bounds[0]),
                float(abs_bounds[1]),
                float(abs_bounds[2]) - self._size.x,
                float(abs_bounds[3]) - self._size.y
            )
        elif isinstance(bounds_param, list):
            # Relative to cursor position
            self._bounds = (
                cursor_screen_pos.x + float(bounds_param[0]),
                cursor_screen_pos.y + float(bounds_param[1]),
                cursor_screen_pos.x + float(bounds_param[2]) - self._size.x,
                cursor_screen_pos.y + float(bounds_param[3]) - self._size.y
            )
        else:
            # Invalid bounds, use unbounded
            self._bounds = None

        # Get stored position or use initial
        if self._position is None:
            self._position = (float(initial_offset[0]), float(initial_offset[1]))

        self._offset = self._position

        # Calculate absolute position
        self._widget_pos = imgui.ImVec2(
            cursor_screen_pos.x + self._offset[0],
            cursor_screen_pos.y + self._offset[1]
        )

        # Clamp to bounds if set
        if self._bounds is not None:
            clamped_x = max(self._bounds[0], min(self._bounds[2], self._widget_pos.x))
            clamped_y = max(self._bounds[1], min(self._bounds[3], self._widget_pos.y))
            if clamped_x != self._widget_pos.x or clamped_y != self._widget_pos.y:
                self._widget_pos = imgui.ImVec2(clamped_x, clamped_y)
                # Update stored offset
                self._offset = (clamped_x - cursor_screen_pos.x, clamped_y - cursor_screen_pos.y)
                self._position = self._offset

        # Save cursor position to restore after rendering
        self._saved_cursor_pos = imgui.get_cursor_pos()

        # Position body at draggable location
        imgui.set_cursor_screen_pos(self._widget_pos)

        # Body is always activated - it renders and handles its own clicks
        self._is_body_activated = True

        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """Handle dragging after body renders"""
        if self._widget_pos is None or self._size is None:
            return Ok(None)

        # Check if mouse is in our bounds
        mouse_pos = imgui.get_mouse_pos()
        in_bounds = (
            self._widget_pos.x <= mouse_pos.x <= self._widget_pos.x + self._size.x and
            self._widget_pos.y <= mouse_pos.y <= self._widget_pos.y + self._size.y
        )

        # Track drag state: start drag only if mouse down in our bounds
        mouse_down = imgui.is_mouse_down(imgui.MouseButton_.left)
        mouse_clicked = imgui.is_mouse_clicked(imgui.MouseButton_.left)

        if mouse_clicked and in_bounds:
            # Mouse just clicked in our area - we might start dragging
            self._drag_active = True

        if not mouse_down:
            # Mouse released - stop tracking drag
            self._drag_active = False

        # Handle dragging only if we started it and mouse is actually dragging
        if self._drag_active and imgui.is_mouse_dragging(imgui.MouseButton_.left):
            drag_delta = imgui.get_mouse_drag_delta(imgui.MouseButton_.left)
            if drag_delta.x != 0 or drag_delta.y != 0:
                new_x = self._widget_pos.x + drag_delta.x
                new_y = self._widget_pos.y + drag_delta.y

                # Clamp to bounds if set
                if self._bounds is not None:
                    new_x = max(self._bounds[0], min(self._bounds[2], new_x))
                    new_y = max(self._bounds[1], min(self._bounds[3], new_y))

                # Convert back to offset
                new_offset_x = new_x - self._cursor_screen_pos.x
                new_offset_y = new_y - self._cursor_screen_pos.y
                self._position = (new_offset_x, new_offset_y)
                imgui.reset_mouse_drag_delta(imgui.MouseButton_.left)

        # Restore cursor position so layout continues normally
        imgui.set_cursor_pos(self._saved_cursor_pos)
        return Ok(None)
