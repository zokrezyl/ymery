"""
Drag widgets - DragInt, DragFloat
"""

from imgui_bundle import imgui
from imery.frontend.widget import Widget
from imery.frontend.decorators import widget
from imery.result import Result, Ok


@widget
class DragInt(Widget):
    """Drag integer widget"""

    def _pre_render_head(self) -> Result[None]:
        if not self._data_path:
            return Result.error("DragInt requires path (id)")

        # Get value using field_values
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"DragInt: failed to get value", value_res)
        value = value_res.unwrapped

        # Validate integer value
        try:
            int_value = int(value)
        except (ValueError, TypeError) as e:
            return Result.error(f"DragInt: invalid integer value '{value}' at path '{self._data_path}'")

        if not isinstance(self._static, dict):
            return Result.error(f"DragInt params must be dict, got {type(self._static)}")

        minv = self._static.get("min", 0)
        maxv = self._static.get("max", 100)
        speed = self._static.get("speed", 1.0)

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
        if not self._data_path:
            return Result.error("DragFloat requires path (id)")

        # Get value using field_values
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"DragFloat: failed to get value", value_res)
        value = value_res.unwrapped

        # Validate float value
        try:
            float_value = float(value)
        except (ValueError, TypeError) as e:
            return Result.error(f"DragFloat: invalid float value '{value}' at path '{self._data_path}'")

        if not isinstance(self._static, dict):
            return Result.error(f"DragFloat params must be dict, got {type(self._static)}")

        minv = float(self._static.get("min", 0.0))
        maxv = float(self._static.get("max", 1.0))
        speed = float(self._static.get("speed", 0.01))

        imgui_id = f"###{self.uid}"

        changed, new_val = imgui.drag_float(imgui_id, float_value, speed, minv, maxv)
        if changed:
            set_res = self._data_bag.set("label", new_val)
            if not set_res:
                return Result.error(f"DragFloat: failed to set value", set_res)

        return Ok(None)
