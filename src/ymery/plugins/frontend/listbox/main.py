"""
ListBox widget
"""

from imgui_bundle import imgui
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok


@widget
class Listbox(Widget):
    """Listbox widget"""

    def _pre_render_head(self) -> Result[None]:
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"Listbox: failed to get value", value_res)
        current_value = value_res.unwrapped

        items = []
        res = self._handle_error(self._data_bag.get("items", items))
        if res:
            items = res.unwrapped

        height = 4
        res = self._handle_error(self._data_bag.get("height", height))
        if res:
            height = res.unwrapped

        try:
            idx = items.index(str(current_value))
        except ValueError:
            idx = 0

        imgui_id = f"###{self.uid}"
        changed, idx = imgui.list_box(imgui_id, idx, items, height)
        if changed and 0 <= idx < len(items):
            set_res = self._data_bag.set("label", items[idx])
            if not set_res:
                return Result.error(f"Listbox: failed to set value", set_res)

        return Ok(None)
