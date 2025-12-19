"""
Spinner widgets - Loading spinners using imspinner
"""

from imgui_bundle import imgui, imspinner
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok


@widget
class SpinnerMovingDots(Widget):
    """SpinnerMovingDots widget"""

    def _pre_render_head(self) -> Result[None]:
        """Render moving dots spinner"""
        label_res = self._data_bag.get("label", "spinner")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "spinner"
        else:
            label = str(label_res) if not isinstance(label_res, str) else label_res

        radius = 20.0
        res = self._handle_error(self._data_bag.get("radius", radius))
        if res:
            radius = res.unwrapped

        thickness = 4.0
        res = self._handle_error(self._data_bag.get("thickness", thickness))
        if res:
            thickness = res.unwrapped

        num_balls = 20
        res = self._handle_error(self._data_bag.get("num_balls", num_balls))
        if res:
            num_balls = res.unwrapped

        color = imgui.ImColor(0.3, 0.5, 0.9, 1.0)
        imspinner.spinner_moving_dots(label, radius, thickness, color, num_balls)

        return Ok(None)


@widget
class SpinnerArcRotation(Widget):
    """SpinnerArcRotation widget"""

    def _pre_render_head(self) -> Result[None]:
        """Render arc rotation spinner"""
        label_res = self._data_bag.get("label", "spinner")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "spinner"
        else:
            label = str(label_res) if not isinstance(label_res, str) else label_res

        radius = imgui.get_font_size() / 1.8
        res = self._handle_error(self._data_bag.get("radius", radius))
        if res:
            radius = res.unwrapped

        thickness = 4.0
        res = self._handle_error(self._data_bag.get("thickness", thickness))
        if res:
            thickness = res.unwrapped

        color = imgui.ImColor(0.3, 0.5, 0.9, 1.0)
        imspinner.spinner_arc_rotation(label, radius, thickness, color)

        return Ok(None)


@widget
class SpinnerAngTriple(Widget):
    """SpinnerAngTriple widget"""

    def _pre_render_head(self) -> Result[None]:
        """Render triple angular spinner"""
        label_res = self._data_bag.get("label", "spinner")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "spinner"
        else:
            label = str(label_res) if not isinstance(label_res, str) else label_res

        radius1 = imgui.get_font_size() / 2.5
        res = self._handle_error(self._data_bag.get("radius1", radius1))
        if res:
            radius1 = res.unwrapped

        radius2 = radius1 * 1.5
        res = self._handle_error(self._data_bag.get("radius2", radius2))
        if res:
            radius2 = res.unwrapped

        radius3 = radius1 * 2.0
        res = self._handle_error(self._data_bag.get("radius3", radius3))
        if res:
            radius3 = res.unwrapped

        thickness = 2.5
        res = self._handle_error(self._data_bag.get("thickness", thickness))
        if res:
            thickness = res.unwrapped

        color = imgui.ImColor(0.3, 0.5, 0.9, 1.0)
        imspinner.spinner_ang_triple(label, radius1, radius2, radius3, thickness, color, color, color)

        return Ok(None)
