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
        if not self._data_path:
            return Result.error("Imguizmo requires path (id)")

        # Get operation from params
        op_str = "translate"
        mode_str = "local"

        if isinstance(self._static, dict):
            op_str = self._static.get("operation", "translate")
            mode_str = self._static.get("mode", "local")

        # Display gizmo info
        imgui.text(f"ImGuizmo: {op_str.upper()} ({mode_str} space)")
        imgui.text("Requires view/projection matrices")
        imgui.text("See ImGuizmo documentation")

        return Ok(None)
