"""
Widget subclasses - primitive widgets for imgui
"""

import math
from imgui_bundle import imgui
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok

import pprint



@widget
class InputText(Widget):
    """Text input widget"""

    def _pre_render_head(self) -> Result[None]:
        res = self._data_bag.get("label")
        if not res:
            return Result.error("InputText: failed to get value", res)
        value = res.unwrapped

        imgui_id = f"###{self.uid}"

        changed, new_val = imgui.input_text(imgui_id, str(value))
        if changed:
            res = self._data_bag.set("label", new_val)
            if not res:
                return Result.error("InputText: failed to set value", res)

        return Ok(None)


@widget
class InputInt(Widget):
    """Integer input widget"""

    def _pre_render_head(self) -> Result[None]:
        res = self._data_bag.get("label")
        if not res:
            return Result.error("InputInt: failed to get value", res)
        value = res.unwrapped

        try:
            int_value = int(value)
        except (ValueError, TypeError):
            return Result.error(f"InputInt: invalid integer value '{value}'")

        imgui_id = f"###{self.uid}"

        changed, new_val = imgui.input_int(imgui_id, int_value)
        if changed:
            res = self._data_bag.set("label", new_val)
            if not res:
                return Result.error("InputInt: failed to set value", res)

        return Ok(None)


@widget
class InputFloat(Widget):
    """Float input widget"""

    def _pre_render_head(self) -> Result[None]:
        res = self._data_bag.get("label")
        if not res:
            return Result.error("InputFloat: failed to get value", res)
        value = res.unwrapped

        try:
            float_value = float(value)
        except (ValueError, TypeError):
            return Result.error(f"InputFloat: invalid float value '{value}'")

        imgui_id = f"###{self.uid}"

        changed, new_val = imgui.input_float(imgui_id, float_value)
        if changed:
            res = self._data_bag.set("label", new_val)
            if not res:
                return Result.error("InputFloat: failed to set value", res)

        return Ok(None)


@widget
class SliderInt(Widget):
    """Integer slider widget"""

    def _pre_render_head(self) -> Result[None]:
        res = self._data_bag.get("label")
        if not res:
            return Result.error("SliderInt: failed to get value", res)
        current_value = res.unwrapped

        minv = 0
        res = self._handle_error(self._data_bag.get("min", minv))
        if res:
            minv = res.unwrapped

        maxv = 100
        res = self._handle_error(self._data_bag.get("max", maxv))
        if res:
            maxv = res.unwrapped

        scale = "linear"
        res = self._handle_error(self._data_bag.get("scale", scale))
        if res:
            scale = res.unwrapped

        display_format = ""
        res = self._handle_error(self._data_bag.get("display-format", display_format))
        if res:
            display_format = res.unwrapped

        if current_value is None or current_value == "":
            current_value = minv
            set_res = self._data_bag.set("label", minv)
            if not set_res:
                return Result.error(f"SliderInt: failed to set default", set_res)

        imgui_id = f"###{self.uid}"

        try:
            current_value = int(current_value)
            minv = int(minv)
            maxv = int(maxv)
        except ValueError as e:
            return Result.error(f"SliderInt: invalid integer value: {e}")

        if scale == "log":
            # Logarithmic scale
            log_min = math.log2(minv)
            log_max = math.log2(maxv)
            log_value = math.log2(current_value)

            if display_format:
                formatted_value = display_format.format(value=current_value)
            else:
                formatted_value = f"2^{int(log_value)} = {current_value}"

            imgui.text(formatted_value)
            changed, log_value = imgui.slider_float(imgui_id, log_value, log_min, log_max, "")

            if changed:
                new_val = int(2 ** log_value)
                set_res = self._data_bag.set("label", new_val)
                if not set_res:
                    return Result.error(f"SliderInt: failed to set value", set_res)
        else:
            # Linear scale
            changed, new_val = imgui.slider_int(imgui_id, current_value, minv, maxv)
            if changed:
                set_res = self._data_bag.set("label", new_val)
                if not set_res:
                    return Result.error(f"SliderInt: failed to set value", set_res)

        return Ok(None)


@widget
class SliderFloat(Widget):
    """Float slider widget"""

    def _pre_render_head(self) -> Result[None]:
        res = self._data_bag.get("label")
        if not res:
            return Result.error("SliderFloat: failed to get value", res)
        current_value = res.unwrapped

        minv = 0.0
        res = self._handle_error(self._data_bag.get("min", minv))
        if res:
            minv = res.unwrapped

        maxv = 1.0
        res = self._handle_error(self._data_bag.get("max", maxv))
        if res:
            maxv = res.unwrapped

        imgui_id = f"###{self.uid}"

        try:
            current_value = float(current_value)
            minv = float(minv)
            maxv = float(maxv)
        except ValueError as e:
            return Result.error(f"SliderFloat: invalid float value: {e}")

        changed, new_val = imgui.slider_float(imgui_id, current_value, minv, maxv)
        if changed:
            set_res = self._data_bag.set("label", new_val)
            if not set_res:
                return Result.error(f"SliderFloat: failed to set value", set_res)

        return Ok(None)

