from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok
from imgui_bundle import imgui


@widget
class Popup(Widget):
    """Popup widget - uses activated event for content"""


    def init(self) -> Result[None]:
        """Initialize popup and call imgui.open_popup()"""
        # Call imgui.open_popup() - first stage of imgui popup creation

        imgui.open_popup(self.uid)
        # Initialize events (including activated)
        return super().init()

    def _pre_render_head(self) -> Result[None]:
        """Render popup - returns True if open, False if closed"""
        # Check if popup is open
        popup_opened = imgui.begin_popup(self.uid)
        self._is_body_activated = popup_opened
        if self._render_cycle == 0:
            # workarround for Popup as in first render cycle it returns always 0
            self._is_open = True
        else:
            self._is_open = popup_opened
            self._is_body_activated = popup_opened
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End popup after rendering"""
        if self._is_body_activated:
            imgui.end_popup()
        return Ok(None)

    def close(self) -> Result[None]:
        """Close the popup."""
        print("Popup: close")
        imgui.close_current_popup()
        return Ok(None)


@widget
class PopupModal(Widget):
    """Popup modal widget - blocks interaction with other windows"""

    def init(self) -> Result[None]:
        """Initialize popup modal and call imgui.open_popup()"""
        res = super().init()
        if not res:
            return Result.error("PopupModal: init: could not init base class", res)
        res = self._data_bag.get("label")
        if not res:
            return Result.error("PopupModal: init: failed to get label", res)

        imgui.open_popup(res.unwrapped)
        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        """Render popup modal - returns True if open, False if closed"""
        # print(f"PopupModal: _pre_render_head: {self._is_body_activated}")

        res = self._data_bag.get("label")
        if not res:
            return Result.error("PopupModal: _pre_render_head: failed to get label", res)

        self._is_body_activated, _ = imgui.begin_popup_modal(res.unwrapped, None, imgui.WindowFlags_.always_auto_resize)

        return Ok(None)

    def close(self) -> Result[None]:
        """Close the popup modal."""
        imgui.close_current_popup()
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End popup modal after rendering"""
        if self._is_body_activated:
            imgui.end_popup()
        return Ok(None)


