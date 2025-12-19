"""
Widget subclasses - primitive widgets for imgui
"""

from imgui_bundle import imgui
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok


@widget
class Text(Widget):
    """Text display widget"""

    def _pre_render_head(self) -> Result[None]:
        res = self._data_bag.get("label")
        if not res:
            return Result.error("Text: failed to get label", res)
        label = str(res.unwrapped)

        width = 0.0
        res_w = self._handle_error(self._data_bag.get("width", width))
        if res_w:
            width = float(res_w.unwrapped)

        if width > 0:
            imgui.begin_child(f"##{self.uid}", (width, imgui.get_text_line_height()))
            imgui.text(label)
            imgui.end_child()
        else:
            imgui.text(label)
        return Ok(None)  # Text widget never opens


@widget
class BulletText(Widget):
    """Bullet text widget - text with bullet point"""

    def _pre_render_head(self) -> Result[None]:
        res = self._data_bag.get("label")
        if not res:
            return Result.error("BulletText: failed to get label", res)
        imgui.bullet_text(res.unwrapped)
        return Ok(None)


@widget
class SeparatorText(Widget):
    """Separator with text label"""

    def _pre_render_head(self) -> Result[None]:
        res = self._data_bag.get("label")
        if not res:
            return Result.error("SeparatorText: failed to get label", res)
        imgui.separator_text(res.unwrapped)
        return Ok(None)


@widget
class Separator(Widget):
    """Separator widget"""

    def _prepare_render(self) -> Result[None]:
        # Separator doesn't need label or metadata
        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        imgui.separator()
        return Ok(None)


@widget
class SameLine(Widget):
    """SameLine widget"""

    def _prepare_render(self) -> Result[None]:
        # SameLine doesn't need label or metadata
        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        imgui.same_line()
        return Ok(None)


@widget
class Combo(Widget):
    """Combo box widget"""
    # TODO ... implement this as similar to other tree like using imgui.begin_combo("combo 1", combo_preview_value, static.flags):
    # similar to


    def _pre_render_head(self) -> Result[None]:
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"Combo: failed to get value", value_res)
        current_value = value_res.unwrapped

        items = []
        res = self._handle_error(self._data_bag.get("items", items))
        if res:
            items = res.unwrapped

        try:
            idx = items.index(str(current_value))
        except ValueError:
            idx = 0

        imgui_id = f"###{self.uid}"
        changed, idx = imgui.combo(imgui_id, idx, items)
        if changed and 0 <= idx < len(items):
            set_res = self._data_bag.set("label", items[idx])
            if not set_res:
                return Result.error(f"Combo: failed to set value", set_res)

        return Ok(None)


@widget
class Checkbox(Widget):
    """Checkbox widget"""


    def _pre_render_head(self) -> Result[None]:
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"Checkbox: failed to get value", value_res)
        current_value = str(value_res.unwrapped).lower() in ("true", "1", "yes")

        imgui_id = f"###{self.uid}"

        changed, new_val = imgui.checkbox(imgui_id, current_value)
        if changed:
            set_res = self._data_bag.set("label", str(new_val))
            if not set_res:
                return Result.error(f"Checkbox: failed to set value", set_res)

        return Ok(None)


@widget
class RadioButton(Widget):
    """Radio button widget"""

    def _pre_render_head(self) -> Result[None]:
        value_res = self._data_bag.get("label")
        if not value_res:
            return Result.error(f"RadioButton: failed to get value", value_res)
        current_value = value_res.unwrapped

        # Get this radio button's value from params
        label_res = self._data_bag.get("label", "")
        button_value = None
        res = self._handle_error(self._data_bag.get("value", button_value))
        if res:
            button_value = res.unwrapped
        if button_value is None:
            return Result.error("RadioButton requires 'value' parameter")

        # Radio button is active if current value matches button value
        active = (current_value == button_value)

        imgui_id = f"###{self.uid}"
        if imgui.radio_button(imgui_id, active):
            # Set the value to this button's value
            set_res = self._data_bag.set("label", button_value)
            if not set_res:
                return Result.error(f"RadioButton: failed to set value", set_res)

        return Ok(None)

