"""
Drag widgets - DragInt, DragFloat
"""

from imgui_bundle import imgui
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok


@widget
class DragInt(Widget):
    """Drag integer widget"""

    def _pre_render_head(self) -> Result[None]:
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"DragInt: failed to get value", value_res)
        value = value_res.unwrapped

        # Validate integer value
        try:
            int_value = int(value)
        except (ValueError, TypeError) as e:
            return Result.error(f"DragInt: invalid integer value '{value}'")

        minv = 0
        res = self._handle_error(self._data_bag.get("min", minv))
        if res:
            minv = res.unwrapped

        maxv = 100
        res = self._handle_error(self._data_bag.get("max", maxv))
        if res:
            maxv = res.unwrapped

        speed = 1.0
        res = self._handle_error(self._data_bag.get("speed", speed))
        if res:
            speed = res.unwrapped

        imgui_id = f"###{self.uid}"

        changed, new_val = imgui.drag_int(imgui_id, int_value, speed, minv, maxv)
        if changed:
            set_res = self._data_bag.set("label", new_val)
            if not set_res:
                return Result.error(f"DragInt: failed to set value", set_res)

        return Ok(None)


@widget
class DragFloat(Widget):
    """Drag float widget"""

    def _pre_render_head(self) -> Result[None]:
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"DragFloat: failed to get value", value_res)
        value = value_res.unwrapped

        # Validate float value
        try:
            float_value = float(value)
        except (ValueError, TypeError) as e:
            return Result.error(f"DragFloat: invalid float value '{value}'")

        minv = 0.0
        res = self._handle_error(self._data_bag.get("min", minv))
        if res:
            minv = float(res.unwrapped)

        maxv = 1.0
        res = self._handle_error(self._data_bag.get("max", maxv))
        if res:
            maxv = float(res.unwrapped)

        speed = 0.01
        res = self._handle_error(self._data_bag.get("speed", speed))
        if res:
            speed = float(res.unwrapped)

        imgui_id = f"###{self.uid}"

        changed, new_val = imgui.drag_float(imgui_id, float_value, speed, minv, maxv)
        if changed:
            set_res = self._data_bag.set("label", new_val)
            if not set_res:
                return Result.error(f"DragFloat: failed to set value", set_res)

        return Ok(None)
