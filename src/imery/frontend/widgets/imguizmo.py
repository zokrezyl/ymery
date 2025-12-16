"""
ImGuizmo widgets - 3D gizmo manipulation
"""

from imgui_bundle import imgui
from imery.frontend.widget import Widget
from imery.frontend.decorators import widget
from imery.result import Result, Ok


@widget
class Imguizmo(Widget):
    """ImGuizmo widget - 3D manipulation gizmo"""

    def _pre_render_head(self) -> Result[None]:
        """Render ImGuizmo"""
        # Get operation from params
        op_str = "translate"
        res = self._handle_error(self._data_bag.get("operation", op_str))
        if res:
            op_str = res.unwrapped

        mode_str = "local"
        res = self._handle_error(self._data_bag.get("mode", mode_str))
        if res:
            mode_str = res.unwrapped

        # Display gizmo info
        imgui.text(f"ImGuizmo: {op_str.upper()} ({mode_str} space)")
        imgui.text("Requires view/projection matrices")
        imgui.text("See ImGuizmo documentation")

        return Ok(None)
