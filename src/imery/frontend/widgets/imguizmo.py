"""
ImGuizmo widgets - 3D gizmo manipulation
Uses numpy for matrix math (no PyGLM dependency for Pyodide compatibility)
"""

import math
import numpy as np
from imgui_bundle import imgui, imguizmo, ImVec2
from imery.frontend.widget import Widget
from imery.decorators import widget
from imery.result import Result, Ok

# ImGuizmo module alias
gizmo = imguizmo.im_guizmo
Matrix16 = gizmo.Matrix16
Matrix3 = gizmo.Matrix3
Matrix6 = gizmo.Matrix6


# ============ Numpy Matrix Math (replaces PyGLM) ============

def perspective(fov_degrees: float, aspect: float, near: float, far: float) -> np.ndarray:
    """Create perspective projection matrix."""
    fov_rad = math.radians(fov_degrees)
    f = 1.0 / math.tan(fov_rad / 2.0)

    result = np.zeros((4, 4), dtype=np.float32)
    result[0, 0] = f / aspect
    result[1, 1] = f
    result[2, 2] = (far + near) / (near - far)
    result[2, 3] = -1.0
    result[3, 2] = (2.0 * far * near) / (near - far)
    return result


def look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
    """Create view matrix looking at target from eye position."""
    eye = np.array(eye, dtype=np.float32)
    target = np.array(target, dtype=np.float32)
    up = np.array(up, dtype=np.float32)

    f = target - eye
    f = f / np.linalg.norm(f)  # normalize

    s = np.cross(f, up)
    s = s / np.linalg.norm(s)  # normalize

    u = np.cross(s, f)

    result = np.eye(4, dtype=np.float32)
    result[0, 0:3] = s
    result[1, 0:3] = u
    result[2, 0:3] = -f
    result[3, 0] = -np.dot(s, eye)
    result[3, 1] = -np.dot(u, eye)
    result[3, 2] = np.dot(f, eye)

    # Transpose to column-major for OpenGL
    return result.T


def mat4_to_list(mat: np.ndarray) -> list:
    """Convert 4x4 numpy matrix to flat list (column-major)."""
    return mat.flatten(order='F').tolist()


def identity_matrix() -> Matrix16:
    """Return identity matrix as Matrix16."""
    return Matrix16([
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0
    ])


# ============ Widgets ============

@widget
class Imguizmo(Widget):
    """Basic ImGuizmo widget - 3D manipulation gizmo

    Displays a 3D gizmo for translate/rotate/scale operations.
    The transformation matrix is stored in data.
    """

    def init(self) -> Result[None]:
        res = super().init()
        if not res:
            return res

        # Initialize object matrix (identity)
        self._object_matrix = identity_matrix()

        # Camera parameters
        self._cam_distance = 8.0
        self._cam_y_angle = 165.0 / 180.0 * math.pi
        self._cam_x_angle = 32.0 / 180.0 * math.pi

        # Gizmo state
        self._current_operation = gizmo.OPERATION.translate
        self._current_mode = gizmo.MODE.local
        self._use_snap = False
        self._snap = Matrix3([1.0, 1.0, 1.0])

        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        """Render ImGuizmo"""
        io = imgui.get_io()

        # Get operation from params
        op_str = "translate"
        res = self._handle_error(self._data_bag.get("operation", op_str))
        if res:
            op_str = res.unwrapped

        # Map string to operation
        op_map = {
            "translate": gizmo.OPERATION.translate,
            "rotate": gizmo.OPERATION.rotate,
            "scale": gizmo.OPERATION.scale,
            "universal": gizmo.OPERATION.universal,
        }
        self._current_operation = op_map.get(op_str, gizmo.OPERATION.translate)

        # Get mode from params
        mode_str = "local"
        res = self._handle_error(self._data_bag.get("mode", mode_str))
        if res:
            mode_str = res.unwrapped
        self._current_mode = gizmo.MODE.local if mode_str == "local" else gizmo.MODE.world

        # Get size from params
        size = [400, 300]
        res = self._handle_error(self._data_bag.get("size", size))
        if res and res.unwrapped:
            size = res.unwrapped

        # Calculate camera matrices
        eye = np.array([
            math.cos(self._cam_y_angle) * math.cos(self._cam_x_angle) * self._cam_distance,
            math.sin(self._cam_x_angle) * self._cam_distance,
            math.sin(self._cam_y_angle) * math.cos(self._cam_x_angle) * self._cam_distance,
        ])
        target = np.array([0.0, 0.0, 0.0])
        up = np.array([0.0, 1.0, 0.0])

        view_mat = look_at(eye, target, up)
        proj_mat = perspective(27.0, size[0] / size[1] if size[1] > 0 else 1.0, 0.1, 100.0)

        camera_view = Matrix16(mat4_to_list(view_mat))
        camera_projection = Matrix16(mat4_to_list(proj_mat))

        # Begin gizmo frame
        gizmo.set_orthographic(False)
        gizmo.begin_frame()

        # Create a child region for the gizmo
        imgui.begin_child("gizmo_region", ImVec2(size[0], size[1]), imgui.ChildFlags_.borders)

        # Set gizmo rect to child window
        pos = imgui.get_window_pos()
        gizmo.set_drawlist()
        gizmo.set_rect(pos.x, pos.y, size[0], size[1])

        # Draw grid
        gizmo.draw_grid(camera_view, camera_projection, identity_matrix(), 100.0)

        # Draw cube
        gizmo.draw_cubes(camera_view, camera_projection, [self._object_matrix])

        # Manipulate gizmo
        gizmo.manipulate(
            camera_view,
            camera_projection,
            self._current_operation,
            self._current_mode,
            self._object_matrix,
            None,
            self._snap if self._use_snap else None,
            None,
            None,
        )

        imgui.end_child()

        # Show status
        if gizmo.is_using():
            imgui.text("Manipulating...")
        elif gizmo.is_over():
            imgui.text("Hover over gizmo")
        else:
            imgui.text(f"Mode: {op_str} ({mode_str})")

        return Ok(None)


@widget
class ImguizmoDemo(Widget):
    """Full ImGuizmo demo with controls

    Interactive demo with operation/mode selection and transform display.
    """

    def init(self) -> Result[None]:
        res = super().init()
        if not res:
            return res

        # Initialize object matrix (identity)
        self._object_matrix = identity_matrix()

        # Camera parameters
        self._cam_distance = 8.0
        self._cam_y_angle = 165.0 / 180.0 * math.pi
        self._cam_x_angle = 32.0 / 180.0 * math.pi
        self._fov = 27.0

        # Gizmo state
        self._current_operation = gizmo.OPERATION.translate
        self._current_mode = gizmo.MODE.local
        self._use_snap = False
        self._snap = Matrix3([1.0, 1.0, 1.0])

        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        """Render ImGuizmo demo with full controls"""
        io = imgui.get_io()

        # Controls
        imgui.text("Operation:")
        imgui.same_line()
        if imgui.radio_button("Translate", self._current_operation == gizmo.OPERATION.translate):
            self._current_operation = gizmo.OPERATION.translate
        imgui.same_line()
        if imgui.radio_button("Rotate", self._current_operation == gizmo.OPERATION.rotate):
            self._current_operation = gizmo.OPERATION.rotate
        imgui.same_line()
        if imgui.radio_button("Scale", self._current_operation == gizmo.OPERATION.scale):
            self._current_operation = gizmo.OPERATION.scale
        imgui.same_line()
        if imgui.radio_button("Universal", self._current_operation == gizmo.OPERATION.universal):
            self._current_operation = gizmo.OPERATION.universal

        imgui.text("Mode:")
        imgui.same_line()
        if imgui.radio_button("Local", self._current_mode == gizmo.MODE.local):
            self._current_mode = gizmo.MODE.local
        imgui.same_line()
        if imgui.radio_button("World", self._current_mode == gizmo.MODE.world):
            self._current_mode = gizmo.MODE.world

        # Camera controls
        changed, self._cam_distance = imgui.slider_float("Distance", self._cam_distance, 1.0, 20.0)
        _, self._fov = imgui.slider_float("FOV", self._fov, 20.0, 110.0)

        # Snap controls
        _, self._use_snap = imgui.checkbox("Use Snap", self._use_snap)
        if self._use_snap:
            snap_values = list(self._snap.values)
            changed, new_snap = imgui.input_float3("Snap", snap_values)
            if changed:
                self._snap = Matrix3(new_snap)

        imgui.separator()

        # Get available size
        avail = imgui.get_content_region_avail()
        gizmo_size = [avail.x, max(300, avail.y - 50)]

        # Calculate camera matrices
        eye = np.array([
            math.cos(self._cam_y_angle) * math.cos(self._cam_x_angle) * self._cam_distance,
            math.sin(self._cam_x_angle) * self._cam_distance,
            math.sin(self._cam_y_angle) * math.cos(self._cam_x_angle) * self._cam_distance,
        ])
        target = np.array([0.0, 0.0, 0.0])
        up = np.array([0.0, 1.0, 0.0])

        view_mat = look_at(eye, target, up)
        proj_mat = perspective(self._fov, gizmo_size[0] / gizmo_size[1] if gizmo_size[1] > 0 else 1.0, 0.1, 100.0)

        camera_view = Matrix16(mat4_to_list(view_mat))
        camera_projection = Matrix16(mat4_to_list(proj_mat))

        # Begin gizmo frame
        gizmo.set_orthographic(False)
        gizmo.begin_frame()

        # Create a child region for the gizmo
        imgui.begin_child("gizmo_demo_region", ImVec2(gizmo_size[0], gizmo_size[1]), imgui.ChildFlags_.borders)

        # Set gizmo rect to child window
        pos = imgui.get_window_pos()
        gizmo.set_drawlist()
        gizmo.set_rect(pos.x, pos.y, gizmo_size[0], gizmo_size[1])

        # Draw grid
        gizmo.draw_grid(camera_view, camera_projection, identity_matrix(), 100.0)

        # Draw cube
        gizmo.draw_cubes(camera_view, camera_projection, [self._object_matrix])

        # Manipulate gizmo
        gizmo.manipulate(
            camera_view,
            camera_projection,
            self._current_operation,
            self._current_mode,
            self._object_matrix,
            None,
            self._snap if self._use_snap else None,
            None,
            None,
        )

        # View manipulate cube in corner
        gizmo.view_manipulate(
            camera_view,
            self._cam_distance,
            ImVec2(pos.x + gizmo_size[0] - 128, pos.y),
            ImVec2(128, 128),
            0x10101010,
        )

        imgui.end_child()

        # Show transform decomposition
        components = gizmo.decompose_matrix_to_components(self._object_matrix)
        imgui.text(f"Position: {components.translation.values[0]:.2f}, {components.translation.values[1]:.2f}, {components.translation.values[2]:.2f}")
        imgui.text(f"Rotation: {components.rotation.values[0]:.1f}, {components.rotation.values[1]:.1f}, {components.rotation.values[2]:.1f}")
        imgui.text(f"Scale: {components.scale.values[0]:.2f}, {components.scale.values[1]:.2f}, {components.scale.values[2]:.2f}")

        return Ok(None)
