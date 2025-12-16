"""
Spinner widgets - Loading spinners using imspinner
"""

from imgui_bundle import imgui, imspinner
from imery.frontend.widget import Widget
from imery.frontend.decorators import widget
from imery.result import Result, Ok


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
        thickness = 4.0
        num_balls = 20
        if isinstance(self._static, dict):
            radius = self._static.get("radius", 20.0)
            thickness = self._static.get("thickness", 4.0)
            num_balls = self._static.get("num_balls", 20)

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
        thickness = 4.0
        if isinstance(self._static, dict):
            radius = self._static.get("radius", radius)
            thickness = self._static.get("thickness", 4.0)

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
        radius2 = radius1 * 1.5
        radius3 = radius1 * 2.0
        thickness = 2.5

        if isinstance(self._static, dict):
            radius1 = self._static.get("radius1", radius1)
            radius2 = self._static.get("radius2", radius2)
            radius3 = self._static.get("radius3", radius3)
            thickness = self._static.get("thickness", 2.5)

        color = imgui.ImColor(0.3, 0.5, 0.9, 1.0)
        imspinner.spinner_ang_triple(label, radius1, radius2, radius3, thickness, color, color, color)

        return Ok(None)
