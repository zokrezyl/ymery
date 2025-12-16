"""
Popup control widgets - OpenPopup, CloseCurrentPopup
"""

from imgui_bundle import imgui
from imery.frontend.widget import Widget
from imery.frontend.decorators import widget
from imery.result import Result, Ok


@widget
class OpenPopup(Widget):
    """Open popup widget"""

    def _prepare_render(self) -> Result[None]:
        # OpenPopup doesn't need data path
        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        if not isinstance(self._static, dict):
            return Result.error(f"OpenPopup params must be dict, got {type(self._static)}")

        popup_id = self._static.get("id")
        if not popup_id:
            return Result.error("OpenPopup requires 'id' parameter")

        imgui.open_popup(popup_id)
        return Ok(None)


@widget
class CloseCurrentPopup(Widget):
    """Close current popup widget"""

    def _prepare_render(self) -> Result[None]:
        # CloseCurrentPopup doesn't need data path
        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        imgui.close_current_popup()
        return Ok(None)
