"""
Widget subclasses - primitive widgets for imgui
"""

import math
from imgui_bundle import imgui
from imery.frontend.widget import Widget
from imery.frontend.decorators import widget
from imery.result import Result, Ok

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
        border = False
        flags = imgui.ChildFlags_.none

        if isinstance(self._static, dict):
            size = self._static.get("size", [0, 0])
            border = self._static.get("border", False)
            flags_list = self._static.get("flags", [])
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
        label = self.uid
        border = True

        if isinstance(self._static, dict):
            count = self._static.get("count", 1)
            label = self._static.get("id", self.uid)
            border = self._static.get("border", True)

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
        has_body = self._body is not None and not self._body.is_empty

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
        pprint.pp(self._data_bag.get_metadata())

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
        if not self._data_path:
            return Result.error("ColorEdit requires path (id)")

        # Get value using field_values
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
        if not self._data_path:
            return Result.error("ColorButton requires path (id)")

        # Get value using field_values
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

    Body can contain any widgets (button, composite, etc.) that will be rendered
    at the draggable position. The invisible button captures drag events while
    the body widgets handle their own interactions (clicks, etc.).

    Parameters:
        size: Size of draggable area [width, height] (default: [30, 30])
        position: Initial position offset [x, y] from parent widget (default: [5, -35])
    """

    # Class-level storage for positions (persists across renders)
    _positions = {}  # {widget_uid: (x, y)}

    def _pre_render_head(self) -> Result[None]:
        """Render draggable container with body widgets"""
        # Get size
        res = self._data_bag.get("size", [30, 30])
        if not res:
            return Result.error("Draggable: failed to get size", res)
        size_list = res.unwrapped
        size = imgui.ImVec2(float(size_list[0]), float(size_list[1]))

        # Get initial position offset
        res = self._data_bag.get("position", [5, -35])
        if not res:
            return Result.error("Draggable: failed to get position", res)
        initial_offset = res.unwrapped

        # Get stored position or use initial
        if self.uid not in Draggable._positions:
            Draggable._positions[self.uid] = (float(initial_offset[0]), float(initial_offset[1]))

        offset = Draggable._positions[self.uid]

        # Get parent widget bounds (where we're positioned relative to)
        # For now, use current cursor screen position as reference
        cursor_screen_pos = imgui.get_cursor_screen_pos()

        # Calculate absolute position
        button_pos = imgui.ImVec2(
            cursor_screen_pos.x + offset[0],
            cursor_screen_pos.y + offset[1]
        )

        # Save cursor position to restore after rendering
        cursor_pos_before = imgui.get_cursor_pos()

        # Render invisible button at absolute position (captures drag events)
        imgui.set_cursor_screen_pos(button_pos)
        imgui.invisible_button(f"##drag_area_{self.uid}", size)

        is_active = imgui.is_item_active()
        is_dragging = is_active and imgui.is_mouse_dragging(imgui.MouseButton_.left)
        is_deactivated = imgui.is_item_deactivated()

        # Check if released without significant drag (this is a click)
        was_clicked_not_dragged = is_deactivated and not is_dragging

        # Handle dragging
        if is_dragging:
            drag_delta = imgui.get_mouse_drag_delta(imgui.MouseButton_.left)
            # Update offset with accumulated drag
            new_offset_x = offset[0] + drag_delta.x
            new_offset_y = offset[1] + drag_delta.y

            # TODO: Add optional bounds clamping if needed
            # For now, allow free positioning

            Draggable._positions[self.uid] = (new_offset_x, new_offset_y)
            imgui.reset_mouse_drag_delta(imgui.MouseButton_.left)

        # Render body widgets at the draggable position
        # Set cursor to button position for body rendering
        imgui.set_cursor_screen_pos(button_pos)

        # Body should be activated to render child widgets
        self._is_body_activated = True

        # If clicked (not dragged), and body exists, tell body button it was clicked
        # We do this AFTER the body renders, so save the flag
        self._was_clicked_not_dragged = was_clicked_not_dragged

        # Note: We don't restore cursor here - let _post_render_head do it
        # Store cursor position to restore later
        self._saved_cursor_pos = cursor_pos_before

        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """Restore cursor position after body rendering and handle click"""
        # If we were clicked (not dragged), make the body think it was clicked
        if hasattr(self, '_was_clicked_not_dragged') and self._was_clicked_not_dragged and self._body:
            # The body should be a button or composite containing a button
            # Traverse to find the button and activate it
            body_widget = self._body

            # If body is composite, get first child (should be the button)
            if hasattr(body_widget, '_children') and body_widget._children and len(body_widget._children) > 0:
                button_widget = body_widget._children[0]
            else:
                button_widget = body_widget

            # Trigger the button's body activation (opens popup)
            if button_widget:
                button_widget._is_body_activated = True

        # Restore cursor position so layout continues normally
        if hasattr(self, '_saved_cursor_pos'):
            imgui.set_cursor_pos(self._saved_cursor_pos)
        return Ok(None)
