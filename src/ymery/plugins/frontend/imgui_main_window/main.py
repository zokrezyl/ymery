"""
Main window widgets for running applications
"""

from imgui_bundle import imgui, implot, immapp
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok

import sys
import yaml

@widget
class ImguiMainWindow(Widget):
    """
    Simple main window using immapp.run()

    Parameters:
        label: Window title (default: "Main Window")
        window-size: Window size as [width, height] (default: [1200, 800])
        fps-idle: FPS when idle (default: 0)
    """

    def init(self) -> Result[None]:
        """Initialize the main window"""
        res = super().init()
        if not res:
            return Result.error("ImguiMainWindow: failed to initialize Widget", res)

        # Get window parameters


        # Initialize ImPlot context
        if not implot.get_current_context():
            implot.create_context()

        # Mark as needing body creation
        self._should_create_body = True

        return Ok(None)

    def _main_loop(self):
        """Main rendering loop called by immapp"""
        if self._body:
            res = self._body.render()
            if not res:
                imgui.text_colored(imgui.ImVec4(1.0, 0.0, 0.0, 1.0), f"Render Error: {res}")
                #print(f"Render Error: {res}")
                yaml_str = yaml.dump(res.as_tree)
                print(yaml_str)
                sys.exit(1)

    def run(self) -> int:
        """Run the application - this is called by app.py"""
        # Create body widget if we have body definition
        body_spec = None
        res = self._data_bag.get("body", body_spec)
        if res:
            body_spec = res.unwrapped
        if body_spec:
            res = self._widget_factory.create_widget(self._data_bag, body_spec, self._namespace)
            if not res:
                print(f"Error creating body widget: {res}")
                return 1
            self._body = res.unwrapped

        res = self._data_bag.get("label", "Main Window")
        if not res:
            print(f"Error creating body widget: {res}")
            return 1

        window_title = res.unwrapped
        res = self._data_bag.get("window-size", [1200, 800])
        if not res:
            print(f"Error creating body widget: {res}")
            return 2
        size_list = res.unwrapped
        window_size = (size_list[0], size_list[1])

        res = self._data_bag.get("fps-idle", 0)
        if not res:
            print(f"Error creating body widget: {res}")
            return 3
        fps_idle = res.unwrapped

        # Run application
        immapp.run(
            gui_function=self._main_loop,
            window_title=window_title,
            window_size=window_size,
            fps_idle=fps_idle
        )
        return 0

    def _pre_render_head(self) -> Result[None]:
        """ImguiMainWindow doesn't render in normal flow"""
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """No cleanup needed"""
        return Ok(None)

