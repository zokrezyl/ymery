"""
Selectable widget
"""

from imgui_bundle import imgui
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok


@widget
class Selectable(Widget):
    """Selectable widget"""

    def _pre_render_head(self) -> Result[None]:
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"Selectable: failed to get value", value_res)
        selected = str(value_res.unwrapped).lower() in ("true", "1", "yes")

        # Get label from params
        label_res = self._data_bag.get("label", "Selectable")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "Selectable"
        else:
            label = label_res

        imgui_id = f"{label}###{self.uid}"

        clicked, new_selected = imgui.selectable(imgui_id, selected)
        if clicked:
            set_res = self._data_bag.set("label", new_selected)
            if not set_res:
                return Result.error(f"Selectable: failed to set value", set_res)

        return Ok(None)
