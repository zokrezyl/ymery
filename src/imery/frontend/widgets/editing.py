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
class InputText(Widget):
    """Text input widget"""

    def _pre_render_head(self) -> Result[None]:
        if not self._data_path:
            return Result.error("InputText requires path (id)")

        # Get value using field_values
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"InputText: failed to get value", value_res)
        value = value_res.unwrapped

        imgui_id = f"###{self.uid}"

        changed, new_val = imgui.input_text(imgui_id, str(value))
        if changed:
            set_res = self._data_bag.set("label", new_val)
            if not set_res:
                return Result.error(f"InputText: failed to set value", set_res)

        return Ok(None)


@widget
class InputInt(Widget):
    """Integer input widget"""

    def _pre_render_head(self) -> Result[None]:
        if not self._data_path:
            return Result.error("InputInt requires path (id)")

        # Get value using field_values
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"InputInt: failed to get value", value_res)
        value = value_res.unwrapped

        # Validate integer value
        try:
            int_value = int(value)
        except (ValueError, TypeError) as e:
            return Result.error(f"InputInt: invalid integer value '{value}' at path '{self._data_path}'")

        imgui_id = f"###{self.uid}"

        changed, new_val = imgui.input_int(imgui_id, int_value)
        if changed:
            set_res = self._data_bag.set("label", new_val)
            if not set_res:
                return Result.error(f"InputInt: failed to set value", set_res)

        return Ok(None)


@widget
class InputFloat(Widget):
    """Float input widget"""

    def _pre_render_head(self) -> Result[None]:
        if not self._data_path:
            return Result.error("InputFloat requires path (id)")

        # Get value using field_values
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"InputFloat: failed to get value", value_res)
        value = value_res.unwrapped

        # Validate float value
        try:
            float_value = float(value)
        except (ValueError, TypeError) as e:
            return Result.error(f"InputFloat: invalid float value '{value}' at path '{self._data_path}'")

        imgui_id = f"###{self.uid}"

        changed, new_val = imgui.input_float(imgui_id, float_value)
        if changed:
            set_res = self._data_bag.set("label", new_val)
            if not set_res:
                return Result.error(f"InputFloat: failed to set value", set_res)

        return Ok(None)


@widget
class SliderInt(Widget):
    """Integer slider widget"""

    def _pre_render_head(self) -> Result[None]:
        if not self._data_path:
            return Result.error("SliderInt requires path (id)")

        # Get value using field_values
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"SliderInt: failed to get value", value_res)
        current_value = value_res.unwrapped

        if not isinstance(self._static, dict):
            return Result.error(f"SliderInt params must be dict, got {type(self._static)}")

        minv = self._static.get("min", 0)
        maxv = self._static.get("max", 100)
        scale = self._static.get("scale", "linear")
        display_format = self._static.get("display-format", None)

        if current_value is None or current_value == "":
            current_value = minv
            set_res = self._data_bag.set("label", minv)
            if not set_res:
                return Result.error(f"SliderInt: failed to set default", set_res)

        imgui_id = f"###{self.uid}"

        if scale == "log":
            # Logarithmic scale
            log_min = math.log2(minv)
            log_max = math.log2(maxv)
            log_value = math.log2(current_value)

            if display_format:
                formatted_value = display_format.format(value=current_value)
            else:
                formatted_value = f"2^{int(log_value)} = {int(current_value)}"

            imgui.text(formatted_value)
            changed, log_value = imgui.slider_float(imgui_id, log_value, log_min, log_max, "")

            if changed:
                new_val = int(2 ** log_value)
                set_res = self._data_bag.set("label", new_val)
                if not set_res:
                    return Result.error(f"SliderInt: failed to set value", set_res)
        else:
            # Linear scale
            changed, new_val = imgui.slider_int(imgui_id, int(current_value), int(minv), int(maxv))
            if changed:
                set_res = self._data_bag.set("label", new_val)
                if not set_res:
                    return Result.error(f"SliderInt: failed to set value", set_res)

        return Ok(None)


@widget
class SliderFloat(Widget):
    """Float slider widget"""

    def _pre_render_head(self) -> Result[None]:
        if not self._data_path:
            return Result.error("SliderFloat requires path (id)")

        # Get value using field_values
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"SliderFloat: failed to get value", value_res)
        current_value = float(value_res.unwrapped)

        if not isinstance(self._static, dict):
            return Result.error(f"SliderFloat params must be dict, got {type(self._static)}")

        minv = float(self._static.get("min", 0.0))
        maxv = float(self._static.get("max", 1.0))

        imgui_id = f"###{self.uid}"

        changed, new_val = imgui.slider_float(imgui_id, current_value, minv, maxv)
        if changed:
            set_res = self._data_bag.set("label", new_val)
            if not set_res:
                return Result.error(f"SliderFloat: failed to set value", set_res)

        return Ok(None)

