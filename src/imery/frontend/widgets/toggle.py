"""
Toggle widgets - Toggle switches using imgui_toggle
"""

from imgui_bundle import imgui, imgui_toggle
from imery.frontend.widget import Widget
from imery.frontend.decorators import widget
from imery.result import Result, Ok


@widget
class Toggle(Widget):
    """Toggle widget - Toggle switch"""

    def _pre_render_head(self) -> Result[None]:
        """Render toggle switch"""
        # Get label
        label_res = self._data_bag.get("label", "Toggle")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "Toggle"
        else:
            label = str(label_res) if not isinstance(label_res, str) else label_res

        # Get current value
        value_res = self._data_bag.get("value", False)
        if isinstance(value_res, Result):
            value = value_res.unwrapped if value_res else False
        else:
            value = value_res

        # Convert to bool
        if isinstance(value, str):
            current_value = value.lower() in ("true", "1", "yes")
        else:
            current_value = bool(value)

        # Get style from params
        flags = 0
        config = None
        if isinstance(self._static, dict):
            style = self._static.get("style", "default")
            animated = self._static.get("animated", False)

            if animated:
                flags = imgui_toggle.ToggleFlags_.animated.value

            if style == "material":
                config = imgui_toggle.material_style()
                if "animation_duration" in self._static:
                    config.animation_duration = self._static["animation_duration"]
            elif style == "ios":
                size_scale = self._static.get("size_scale", 0.2)
                light_mode = self._static.get("light_mode", False)
                config = imgui_toggle.ios_style(size_scale=size_scale, light_mode=light_mode)

        # Render toggle
        imgui_id = f"##{label}_{self.uid}"
        if config is not None:
            changed, new_value = imgui_toggle.toggle(imgui_id, current_value, config=config)
        else:
            changed, new_value = imgui_toggle.toggle(imgui_id, current_value, flags)

        # Display label
        imgui.same_line()
        imgui.text(label)

        # Update value if changed
        if changed and self._data_path:
            set_res = self._data_bag.set("value", new_value)
            if not set_res:
                return Result.error(f"Toggle: failed to set value", set_res)

        return Ok(None)
