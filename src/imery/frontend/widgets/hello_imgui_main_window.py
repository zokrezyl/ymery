"""
Main window widgets for running applications
"""

from imgui_bundle import imgui, implot, implot3d, imgui_md, immapp, hello_imgui
from imery.frontend.widget import Widget
from imery.frontend.composite import Composite
from imery.frontend.decorators import widget
from imery.types import DataPath
from imery.backend.types import TreeLike
from imery.result import Result, Ok
from imery.frontend.widgets.docking import DockableWindow, DockingSplit
from imery.frontend.widgets.tree_like import MainMenuBar

from typing import Optional, Dict, List
import sys
import pprint
import yaml



@widget
class HelloImguiMainWindow(Composite):
    """
    Main window using hello_imgui.run() with docking support

    Parameters:
        window-title: Window title (default: "Imery App")
        window-size: Window size as [width, height] (default: [1200, 800])
        fps-idle: FPS when idle (default: 0)

    Body can contain:
        - DockingSplit widgets (define dock space layout)
        - DockableWindow widgets (dockable windows)
        - Other widgets (rendered in main dock space if no docking)
    """

    def init(self) -> Result[None]:
        """Initialize the main window"""
        res = super().init()
        if not res:
            return Result.error("HelloImguiMainWindow: failed to initialize Widget", res)

        # Initialize ImPlot context
        if not implot.get_current_context():
            implot.create_context()

        # Initialize ImPlot3D context
        if not implot3d.get_current_context():
            implot3d.create_context()

        # Initialize Markdown
        imgui_md.initialize_markdown()

        return Ok(None)


    def _render_menu_bar(self):
        """Render the menu bar"""
        if self._menu_bar_widget:
            self._handle_error(self._menu_bar_widget.render())

    def _main_loop(self):
        """Main rendering loop called by hello_imgui"""
        imgui.text("Main loop is running!")
        # Render non-docking widgets (regular widgets in main dock space)
        for widget in self._non_docking_widgets:
            self._handle_error(widget.render())

        self._render_errors()

    def _resolve_constant(self, field_name: str, value: str):
        """Convert YAML constant to Python constant

        Examples:
        - field: default-imgui-window-type, value: provide-full-screen-dock-space
          → hello_imgui.DefaultImGuiWindowType.provide_full_screen_dock_space
        - field: direction, value: down
          → imgui.Dir.down
        """
        # Replace hyphens with underscores
        py_value = value.replace('-', '_')

        # Map field names to namespace
        constant_map = {
            'default-imgui-window-type': 'hello_imgui.DefaultImGuiWindowType',
            'direction': 'imgui.Dir',
        }

        if field_name in constant_map:
            namespace = constant_map[field_name]
            return eval(f"{namespace}.{py_value}")

        return value

    def _process_params_dict(self, d: dict, parent_key: str = "") -> dict:
        """Recursively process dict, resolving constants"""
        result = {}
        for key, value in d.items():
            full_key = f"{parent_key}.{key}" if parent_key else key

            if isinstance(value, dict):
                result[key.replace('-', '_')] = self._process_params_dict(value, full_key)
            elif isinstance(value, str):
                # Try to resolve as constant
                result[key.replace('-', '_')] = self._resolve_constant(key, value)
            elif isinstance(value, list):
                result[key.replace('-', '_')] = value
            else:
                result[key.replace('-', '_')] = value

        return result

    def _read_runner_params_metadata(self) -> dict:
        """Read runner-params metadata and convert to Python dict"""
        res = self._data_bag.get("runner-params", {})
        if not res:
            return {}

        params_dict = res.unwrapped
        # Recursively process dict to resolve constants
        return self._process_params_dict(params_dict)

    def run(self) -> Result[None]:
        """Run the application - this is called by app.py"""
        # Initialize children
        res = self.children
        if not res:
            return 1
        children = res.unwrapped

        self._non_docking_widgets = []
        self._menu_bar_widget = None
        # Extract children by type
        docking_splits = []
        dockable_windows = []
        menu_widget = None
        app_menu_items_widget = None

        for child in children:
            if isinstance(child, DockingSplit):
                docking_splits.append(child)
            elif isinstance(child, DockableWindow):
                dockable_windows.append(child)
            elif isinstance(child, MainMenuBar):
                if self._menu_bar_widget is not None:
                    self._handle_error(Result.error("HelloImguiMainWindow: multiple MainMenuBar widgets found, only one allowed"))
                else:
                    self._menu_bar_widget = child
            elif child.__class__.__name__ == "HelloImguiMenu":
                if menu_widget is not None:
                    self._handle_error(Result.error("HelloImguiMainWindow: multiple HelloImguiMenu widgets found, only one allowed"))
                else:
                    menu_widget = child
            elif child.__class__.__name__ == "HelloImguiAppMenuItems":
                if app_menu_items_widget is not None:
                    self._handle_error(Result.error("HelloImguiMainWindow: multiple HelloImguiAppMenuItems widgets found, only one allowed"))
                else:
                    app_menu_items_widget = child
            else:
                # Other widgets render in main loop
                self._non_docking_widgets.append(child)

        # Setup hello_imgui RunnerParams
        runner_params = hello_imgui.RunnerParams()

        # Read and apply runner-params metadata
        params_dict = self._read_runner_params_metadata()

        # Apply app_window_params
        if 'app_window_params' in params_dict:
            for key, val in params_dict['app_window_params'].items():
                if key == 'window_geometry' and isinstance(val, dict):
                    for gkey, gval in val.items():
                        setattr(runner_params.app_window_params.window_geometry, gkey, gval)
                else:
                    setattr(runner_params.app_window_params, key, val)

        # Apply imgui_window_params
        if 'imgui_window_params' in params_dict:
            for key, val in params_dict['imgui_window_params'].items():
                setattr(runner_params.imgui_window_params, key, val)

        # Fallback to old fields if not in runner-params
        res = self._data_bag.get("label", self.uid)
        if not res:
            self._handle_error(Result.error("HelloImguiMainWindow: failed to get label", res))
            label = "error: LABEL NOT AVAILABLE"
        else:
            label = res.unwrapped
        if 'app_window_params' not in params_dict:
            runner_params.app_window_params.window_title = label

        res = self._data_bag.get("window-size", [1200, 800])
        if not res:
            self._handle_error(Result.error("HelloImguiMainWindow: failed to get window-size", res))
            size_list = [1200, 800]
        else:
            size_list = res.unwrapped

        if 'app_window_params' not in params_dict:
            runner_params.app_window_params.window_geometry.size = (size_list[0], size_list[1])

        # If we have dockable windows or docking splits, enable docking
        if dockable_windows or docking_splits:
            runner_params.imgui_window_params.default_imgui_window_type = (
                hello_imgui.DefaultImGuiWindowType.provide_full_screen_dock_space
            )

            # Setup docking params - create complete DockingParams object
            docking_params = hello_imgui.DockingParams()

            # Set layout condition to always apply the layout
            docking_params.layout_condition = hello_imgui.DockingLayoutCondition.application_start

            # Add docking splits
            docking_params.docking_splits = [split_widget.docking_split for split_widget in docking_splits]

            # Add dockable windows
            docking_params.dockable_windows = [window_widget.dockable_window for window_widget in dockable_windows]

            # Assign the complete DockingParams to runner_params
            runner_params.docking_params = docking_params

        # Set main GUI function
        runner_params.callbacks.show_gui = self._main_loop

        # Load markdown fonts
        runner_params.callbacks.load_additional_fonts = imgui_md.get_font_loader_function()

        # Set menu bar callback if menu bar widget exists
        if self._menu_bar_widget:
            runner_params.imgui_window_params.show_menu_bar = True
            runner_params.callbacks.show_menus = self._render_menu_bar

        # Set HelloImGui menu callbacks
        if menu_widget:
            runner_params.imgui_window_params.show_menu_bar = True
            runner_params.callbacks.show_menus = lambda: menu_widget.render()

        if app_menu_items_widget:
            runner_params.callbacks.show_app_menu_items = lambda: app_menu_items_widget.render()

        res = self._data_bag.get("fps-idle", 0)
        if not res:
            self._handle_error(Result.error("HelloImguiMainWindow: failed to get 'fps-idle'"))
            idle = 0
        else:
            idle = res.unwrapped
        runner_params.fps_idling.fps_idle = idle

        # Run application
        hello_imgui.run(runner_params)

        return Ok[None]

    def _pre_render_head(self) -> Result[None]:
        """HelloImguiMainWindow doesn't render in normal flow"""
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """No cleanup needed"""
        return Ok(None)
