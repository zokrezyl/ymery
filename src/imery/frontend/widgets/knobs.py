"""
Knobs widgets - Rotary knobs using imgui_knobs
"""

from imgui_bundle import imgui, imgui_knobs, immapp
from imery.frontend.widget import Widget
from imery.frontend.decorators import widget
from imery.result import Result, Ok


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
        v_max = 1.0
        size = immapp.em_size() * 2.5
        variant = imgui_knobs.ImGuiKnobVariant_.tick
        format_str = "%.2f"
        speed = 0
        steps = 100

        if isinstance(self._static, dict):
            v_min = self._static.get("min", 0.0)
            v_max = self._static.get("max", 1.0)
            size = self._static.get("size", size)
            format_str = self._static.get("format", "%.2f")
            speed = self._static.get("speed", 0)
            steps = self._static.get("steps", 100)

            variant_name = self._static.get("variant", "tick")
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

        # Render knob
        changed, new_value = imgui_knobs.knob(
            label,
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
        if changed and self._data_path:
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
        v_max = 15
        size = immapp.em_size() * 2.5
        variant = imgui_knobs.ImGuiKnobVariant_.tick
        format_str = "%02i"
        speed = 0
        steps = 10

        if isinstance(self._static, dict):
            v_min = self._static.get("min", 0)
            v_max = self._static.get("max", 15)
            size = self._static.get("size", size)
            format_str = self._static.get("format", "%02i")
            speed = self._static.get("speed", 0)
            steps = self._static.get("steps", 10)

            variant_name = self._static.get("variant", "tick")
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

        # Render knob
        changed, new_value = imgui_knobs.knob_int(
            label,
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
        if changed and self._data_path:
            set_res = self._data_bag.set("value", new_value)
            if not set_res:
                return Result.error(f"KnobInt: failed to set value", set_res)

        return Ok(None)
