"""
Knobs widgets - Rotary knobs using imgui_knobs
"""

from imgui_bundle import imgui, imgui_knobs, immapp
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok


@widget
class Knob(Widget):
    """Knob widget - Rotary knob (float)"""

    def _pre_render_head(self) -> Result[None]:
        """Render knob"""
        # Get label
        label_res = self._data_bag.get("label", "Knob")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "Knob"
        else:
            label = str(label_res) if not isinstance(label_res, str) else label_res

        # Get current value
        value_res = self._data_bag.get("value", 0.0)
        if isinstance(value_res, Result):
            value = value_res.unwrapped if value_res else 0.0
        else:
            value = value_res

        # Get params
        v_min = 0.0
        res = self._handle_error(self._data_bag.get("min", v_min))
        if res:
            v_min = res.unwrapped

        v_max = 1.0
        res = self._handle_error(self._data_bag.get("max", v_max))
        if res:
            v_max = res.unwrapped

        size = immapp.em_size() * 2.5
        res = self._handle_error(self._data_bag.get("size", size))
        if res:
            size = res.unwrapped

        format_str = "%.2f"
        res = self._handle_error(self._data_bag.get("format", format_str))
        if res:
            format_str = res.unwrapped

        speed = 0
        res = self._handle_error(self._data_bag.get("speed", speed))
        if res:
            speed = res.unwrapped

        steps = 100
        res = self._handle_error(self._data_bag.get("steps", steps))
        if res:
            steps = res.unwrapped

        variant_name = "tick"
        res = self._handle_error(self._data_bag.get("variant", variant_name))
        if res:
            variant_name = res.unwrapped
        variant_map = {
            "tick": imgui_knobs.ImGuiKnobVariant_.tick,
            "dot": imgui_knobs.ImGuiKnobVariant_.dot,
            "space": imgui_knobs.ImGuiKnobVariant_.space,
            "stepped": imgui_knobs.ImGuiKnobVariant_.stepped,
            "wiper": imgui_knobs.ImGuiKnobVariant_.wiper,
            "wiper_dot": imgui_knobs.ImGuiKnobVariant_.wiper_dot,
            "wiper_only": imgui_knobs.ImGuiKnobVariant_.wiper_only,
        }
        variant = variant_map.get(variant_name, imgui_knobs.ImGuiKnobVariant_.tick)

        # Render knob with unique ID
        changed, new_value = imgui_knobs.knob(
            f"{label}##{self._uid}",
            p_value=float(value),
            v_min=v_min,
            v_max=v_max,
            speed=speed,
            format=format_str,
            variant=variant.value,
            size=size,
            flags=0,
            steps=steps,
        )

        # Update value if changed
        if changed:
            set_res = self._data_bag.set("value", new_value)
            if not set_res:
                return Result.error(f"Knob: failed to set value", set_res)

        return Ok(None)


@widget
class KnobInt(Widget):
    """KnobInt widget - Rotary knob (int)"""

    def _pre_render_head(self) -> Result[None]:
        """Render int knob"""
        # Get label
        label_res = self._data_bag.get("label", "Knob")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "Knob"
        else:
            label = str(label_res) if not isinstance(label_res, str) else label_res

        # Get current value
        value_res = self._data_bag.get("value", 0)
        if isinstance(value_res, Result):
            value = value_res.unwrapped if value_res else 0
        else:
            value = value_res

        # Get params
        v_min = 0
        res = self._handle_error(self._data_bag.get("min", v_min))
        if res:
            v_min = res.unwrapped

        v_max = 15
        res = self._handle_error(self._data_bag.get("max", v_max))
        if res:
            v_max = res.unwrapped

        size = immapp.em_size() * 2.5
        res = self._handle_error(self._data_bag.get("size", size))
        if res:
            size = res.unwrapped

        format_str = "%02i"
        res = self._handle_error(self._data_bag.get("format", format_str))
        if res:
            format_str = res.unwrapped

        speed = 0
        res = self._handle_error(self._data_bag.get("speed", speed))
        if res:
            speed = res.unwrapped

        steps = 10
        res = self._handle_error(self._data_bag.get("steps", steps))
        if res:
            steps = res.unwrapped

        variant_name = "tick"
        res = self._handle_error(self._data_bag.get("variant", variant_name))
        if res:
            variant_name = res.unwrapped
        variant_map = {
            "tick": imgui_knobs.ImGuiKnobVariant_.tick,
            "dot": imgui_knobs.ImGuiKnobVariant_.dot,
            "space": imgui_knobs.ImGuiKnobVariant_.space,
            "stepped": imgui_knobs.ImGuiKnobVariant_.stepped,
            "wiper": imgui_knobs.ImGuiKnobVariant_.wiper,
            "wiper_dot": imgui_knobs.ImGuiKnobVariant_.wiper_dot,
            "wiper_only": imgui_knobs.ImGuiKnobVariant_.wiper_only,
        }
        variant = variant_map.get(variant_name, imgui_knobs.ImGuiKnobVariant_.tick)

        # Render knob with unique ID
        changed, new_value = imgui_knobs.knob_int(
            f"{label}##{self._uid}",
            p_value=int(value),
            v_min=v_min,
            v_max=v_max,
            speed=speed,
            format=format_str,
            variant=variant.value,
            steps=steps,
            size=size,
        )

        # Update value if changed
        if changed:
            set_res = self._data_bag.set("value", new_value)
            if not set_res:
                return Result.error(f"KnobInt: failed to set value", set_res)

        return Ok(None)
