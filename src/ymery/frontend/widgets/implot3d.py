"""
ImPlot3D widgets - 3D plotting
"""

from imgui_bundle import imgui, implot3d
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok


@widget
class Implot3d(Widget):
    """ImPlot3D widget - 3D plot container"""

    def _pre_render_head(self) -> Result[None]:
        """Begin 3D plot"""
        label_res = self._data_bag.get("label", "3D Plot")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "3D Plot"
        else:
            label = label_res

        # Get size from params
        size = [-1, -1]
        res = self._handle_error(self._data_bag.get("size", size))
        if res:
            size = res.unwrapped

        plot_opened = implot3d.begin_plot(label, size)
        self._is_body_activated = plot_opened
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End 3D plot"""
        if self._is_body_activated:
            implot3d.end_plot()
        return Ok(None)
