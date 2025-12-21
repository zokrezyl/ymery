"""
Main window widgets for running applications
"""

from imgui_bundle import imgui, implot, implot3d, imgui_md, hello_imgui
from ymery.frontend.widget import Widget
from ymery.frontend.composite import Composite
from ymery.decorators import widget
from ymery.result import Result, Ok


@widget
class HelloImguiMainWindow(Composite):
    """
    Main window using hello_imgui.run() with docking support

    Parameters:
        label: Window title (default: widget UID)
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

        # Check dock tab hover and show tooltips for dockable windows
        self._check_dock_tab_tooltips()

        # Render non-docking widgets (regular widgets in main dock space)
        for widget in self._non_docking_widgets:
            self._handle_error(widget.render())

        self._render_errors()

    def _check_dock_tab_tooltips(self):
        """Check if any dock tab is hovered and show its tooltip"""
        for dockable_window in self._dockable_windows:
            if not dockable_window._dock_tab_tooltip:
                continue
            try:
                window = imgui.internal.find_window_by_name(dockable_window._dockable_window.label)
                if window:
                    # Check if dock tab is hovered (hovered_rect flag = 1)
                    # ItemStatusFlags_.hovered_rect = 1 << 0 = 1
                    if window.dc.dock_tab_item_status_flags & 1:
                        imgui.set_tooltip(dockable_window._dock_tab_tooltip)
                        break  # Only one tooltip at a time
            except Exception:
                pass  # Silently ignore if window not found or API unavailable

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
        self._dockable_windows = []  # Store for dock tab tooltip checking
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
            elif child.__class__.__name__ ==  "MainMenuBar":
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

            # Store dockable windows for dock tab tooltip checking
            self._dockable_windows = dockable_windows

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

"""
HelloImGui-specific widgets for menu bar integration
"""


@widget
class HelloImguiMenu(Composite):
    """HelloImGui menu bar contents widget

    Renders children inside HelloImGui's menu bar context.
    HelloImGui handles begin_main_menu_bar() / end_main_menu_bar() automatically.
    This widget just renders its Menu children.
    """
    pass  # No overrides needed - Composite handles rendering children


@widget
class HelloImguiAppMenuItems(Composite):
    """HelloImGui app menu items widget

    Adds custom items to the HelloImGui App menu.
    Children should be menu-item widgets.
    """
    pass  # No overrides needed - Composite handles rendering children



"""
Docking widgets for hello_imgui docking system
"""



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

        # Get tooltip for dock tab
        res = self._data_bag.get("tooltip", None)
        self._dock_tab_tooltip = res.unwrapped if res else None

        # Set gui_function to render the body
        self._dockable_window.gui_function = self._render_dockable

        return Ok(None)

    def _render_dockable(self):
        res = self.render()
        if not res:
            # TODO use the render_error from widget.py to display the error!
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
