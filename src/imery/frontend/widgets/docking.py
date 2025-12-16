"""
Docking widgets for hello_imgui docking system
"""

from imgui_bundle import imgui, hello_imgui
from imery.frontend.widget import Widget
from imery.frontend.decorators import widget
from imery.types import DataPath
from imery.backend.types import TreeLike
from imery.result import Result, Ok

from typing import Optional, Dict


@widget
class DockableWindow(Widget):
    """
    Dockable window widget - creates a window that can be docked in the hello_imgui docking system

    Parameters:
        label: Window title
        dock-space-name: Name of the dock space to dock to
        include-in-view-menu: Whether to include in View menu (default: True)
        remember-is-visible: Whether to remember visibility state (default: True)
        is-visible: Initial visibility state (default: True)
        can-be-closed: Whether window can be closed (default: True)
    """

    def init(self) -> Result[None]:
        """Initialize the dockable window"""
        self._dockable_window = None
        res = super().init()
        if not res:
            return Result.error("DockableWindow: failed to initialize Widget", res)

        # Create hello_imgui.DockableWindow instance
        self._dockable_window = hello_imgui.DockableWindow()

        # Get label
        res = self._data_bag.get("label")
        if not res:
            return Result.error("DockableWindow: failed to get label", res)
        self._dockable_window.label = res.unwrapped

        # Get dock_space_name (optional)
        res = self._data_bag.get("dock-space-name", "MainDockSpace")
        if res:
            self._dockable_window.dock_space_name = res.unwrapped

        # Get optional parameters
        res = self._data_bag.get("include-in-view-menu", True)
        if res:
            self._dockable_window.include_in_view_menu = res.unwrapped

        res = self._data_bag.get("remember-is-visible", True)
        if res:
            self._dockable_window.remember_is_visible = res.unwrapped

        res = self._data_bag.get("is-visible", True)
        if res:
            self._dockable_window.is_visible = res.unwrapped

        res = self._data_bag.get("can-be-closed", True)
        if res:
            self._dockable_window.can_be_closed = res.unwrapped

        # Set gui_function to render the body
        self._dockable_window.gui_function = self._render_dockable

        return Ok(None)

    def _render_dockable(self):
        res = self.render()
        if not res:
            print("Failed to render dockable window")
            import yaml
            print(yaml.dump(res.as_tree))
            import sys
            sys.exit(-1)

    def _pre_render_head(self) -> Result[None]:
        """DockableWindow doesn't render in the normal flow - it's handled by hello_imgui"""
        # Mark as activated so body gets created and rendered
        self._is_body_activated = True
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """No cleanup needed"""
        return Ok(None)


    @property
    def dockable_window(self):
        """Get the hello_imgui.DockableWindow instance"""
        return self._dockable_window

    def dispose(self) -> Result[None]:
        """Cleanup"""
        return Ok(None)


@widget
class DockingSplit(Widget):
    """
    Docking split widget - defines how to split a dock space into multiple regions

    Parameters:
        initial-dock: Name of the initial dock space to split
        new-dock: Name of the new dock space to create
        direction: Direction to split (up, down, left, right)
        ratio: Ratio of the split (0.0 to 1.0)
        body: Optional list of DockableWindow widgets that will automatically use new-dock as their dock-space-name
    """

    def init(self) -> Result[None]:
        """Initialize the docking split"""
        res = super().init()
        if not res:
            return Result.error("DockingSplit: failed to initialize Widget", res)

        # Create hello_imgui.DockingSplit instance
        self._docking_split = hello_imgui.DockingSplit()

        # Get initial-dock
        res = self._data_bag.get("initial-dock")
        if not res:
            return Result.error("DockingSplit: failed to get initial-dock", res)
        self._docking_split.initial_dock = res.unwrapped

        # Get new-dock
        res = self._data_bag.get("new-dock")
        if not res:
            return Result.error("DockingSplit: failed to get new-dock", res)
        self._docking_split.new_dock = res.unwrapped

        # Get direction
        res = self._data_bag.get("direction", "down")
        if not res:
            return Result.error("DockingSplit: failed to get direction", res)

        direction_str = res.unwrapped
        direction_map = {
            "up": imgui.Dir_.up,
            "down": imgui.Dir_.down,
            "left": imgui.Dir_.left,
            "right": imgui.Dir_.right
        }

        if direction_str not in direction_map:
            return Result.error(f"DockingSplit: invalid direction '{direction_str}', must be one of: up, down, left, right")

        self._docking_split.direction = direction_map[direction_str]

        # Get ratio
        res = self._data_bag.get("ratio", 0.5)
        if not res:
            return Result.error("DockingSplit: failed to get ratio", res)
        self._docking_split.ratio = float(res.unwrapped)

        return Ok(None)


    def render(self) -> Result[None]:
        """DockingSplit doesn't render - it's configuration only"""
        return Ok(None)

    @property
    def docking_split(self):
        """Get the hello_imgui.DockingSplit instance"""
        return self._docking_split

    def dispose(self) -> Result[None]:
        """Cleanup"""
        return Ok(None)
