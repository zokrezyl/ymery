"""
NanoVG widgets - Vector graphics rendering
"""

from imgui_bundle import imgui, nanovg as nvg, hello_imgui, ImVec2
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok
import math

nvg_imgui = nvg.nvg_imgui


@widget
class NanovgCanvas(Widget):
    """NanoVG Canvas widget - Vector graphics rendering with framebuffer"""

    def init(self) -> Result[None]:
        """Initialize NanoVG context and framebuffer"""
        res = super().init()
        if not res:
            return res

        # Create NanoVG context
        self._vg = nvg_imgui.create_nvg_context_hello_imgui(
            nvg_imgui.NvgCreateFlags.antialias.value | nvg_imgui.NvgCreateFlags.stencil_strokes.value
        )

        # Get size from params
        size = [800, 600]
        res = self._handle_error(self._data_bag.get("size", size))
        if res:
            size = res.unwrapped
        width, height = size[0], size[1]

        # Create framebuffer
        nvg_image_flags = 0
        self._nvg_framebuffer = nvg_imgui.NvgFramebuffer(self._vg, width, height, nvg_image_flags)

        # Load font for text rendering
        font_path = hello_imgui.asset_file_full_path("fonts/Roboto/Roboto-Regular.ttf")
        self._font_id = nvg.create_font(self._vg, "roboto", font_path)

        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        """Render NanoVG canvas"""
        # Get label
        label_res = self._data_bag.get("label", "NanoVG Canvas")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "NanoVG Canvas"
        else:
            label = label_res

        # Get canvas type from params
        canvas_type = "demo"
        res = self._handle_error(self._data_bag.get("type", canvas_type))
        if res:
            canvas_type = res.unwrapped

        # Render to framebuffer based on type
        if canvas_type == "shapes":
            nvg_imgui.render_nvg_to_frame_buffer(self._vg, self._nvg_framebuffer, self._draw_shapes)
        elif canvas_type == "gradients":
            nvg_imgui.render_nvg_to_frame_buffer(self._vg, self._nvg_framebuffer, self._draw_gradients)
        elif canvas_type == "text":
            nvg_imgui.render_nvg_to_frame_buffer(self._vg, self._nvg_framebuffer, self._draw_text)
        elif canvas_type == "heart":
            nvg_imgui.render_nvg_to_frame_buffer(self._vg, self._nvg_framebuffer, self._draw_heart)
        else:
            nvg_imgui.render_nvg_to_frame_buffer(self._vg, self._nvg_framebuffer, self._draw_demo)

        # Display framebuffer as ImGui image
        imgui.text(label)
        imgui.image(
            imgui.ImTextureRef(self._nvg_framebuffer.texture_id),
            ImVec2(self._nvg_framebuffer.width, self._nvg_framebuffer.height)
        )

        return Ok(None)

    def _draw_demo(self, vg: nvg.Context, width: float, height: float):
        """Draw demo scene with shapes and gradients"""
        nvg.save(vg)

        # White background
        nvg.begin_path(vg)
        nvg.rect(vg, 0, 0, width, height)
        nvg.fill_color(vg, nvg.rgba(255, 255, 255, 255))
        nvg.fill(vg)

        # Draw rectangles with gradients
        nvg.begin_path(vg)
        nvg.rect(vg, 50, 50, 200, 150)
        paint = nvg.linear_gradient(vg, 50, 50, 250, 200, nvg.rgba(255, 0, 0, 255), nvg.rgba(0, 0, 255, 255))
        nvg.fill_paint(vg, paint)
        nvg.fill(vg)

        # Draw circles
        nvg.begin_path(vg)
        nvg.circle(vg, width - 150, 150, 80)
        nvg.fill_color(vg, nvg.rgba(0, 255, 0, 200))
        nvg.fill(vg)
        nvg.stroke_color(vg, nvg.rgba(0, 100, 0, 255))
        nvg.stroke_width(vg, 3)
        nvg.stroke(vg)

        # Draw rounded rectangle
        nvg.begin_path(vg)
        nvg.rounded_rect(vg, 50, 250, 300, 100, 20)
        radial = nvg.radial_gradient(vg, 200, 300, 20, 150, nvg.rgba(255, 255, 0, 255), nvg.rgba(255, 0, 255, 255))
        nvg.fill_paint(vg, radial)
        nvg.fill(vg)

        # Draw text
        if self._font_id >= 0:
            nvg.font_size(vg, 48)
            nvg.font_face_id(vg, self._font_id)
            nvg.fill_color(vg, nvg.rgba(0, 0, 0, 255))
            nvg.text(vg, 50, height - 50, "NanoVG Demo")

        nvg.restore(vg)

    def _draw_shapes(self, vg: nvg.Context, width: float, height: float):
        """Draw various shapes"""
        nvg.save(vg)

        # Background
        nvg.begin_path(vg)
        nvg.rect(vg, 0, 0, width, height)
        nvg.fill_color(vg, nvg.rgba(240, 240, 240, 255))
        nvg.fill(vg)

        # Rectangle
        nvg.begin_path(vg)
        nvg.rect(vg, 50, 50, 150, 100)
        nvg.fill_color(vg, nvg.rgba(255, 100, 100, 255))
        nvg.fill(vg)
        nvg.stroke_color(vg, nvg.rgba(150, 0, 0, 255))
        nvg.stroke_width(vg, 2)
        nvg.stroke(vg)

        # Rounded rectangle
        nvg.begin_path(vg)
        nvg.rounded_rect(vg, 250, 50, 150, 100, 15)
        nvg.fill_color(vg, nvg.rgba(100, 255, 100, 255))
        nvg.fill(vg)

        # Circle
        nvg.begin_path(vg)
        nvg.circle(vg, 125, 250, 60)
        nvg.fill_color(vg, nvg.rgba(100, 100, 255, 255))
        nvg.fill(vg)

        # Ellipse
        nvg.begin_path(vg)
        nvg.ellipse(vg, 325, 250, 80, 50)
        nvg.fill_color(vg, nvg.rgba(255, 255, 100, 255))
        nvg.fill(vg)

        # Line path
        nvg.begin_path(vg)
        nvg.move_to(vg, 50, 400)
        nvg.line_to(vg, 150, 350)
        nvg.line_to(vg, 250, 400)
        nvg.line_to(vg, 350, 350)
        nvg.stroke_color(vg, nvg.rgba(255, 0, 255, 255))
        nvg.stroke_width(vg, 4)
        nvg.stroke(vg)

        nvg.restore(vg)

    def _draw_gradients(self, vg: nvg.Context, width: float, height: float):
        """Draw gradient examples"""
        nvg.save(vg)

        # Background
        nvg.begin_path(vg)
        nvg.rect(vg, 0, 0, width, height)
        nvg.fill_color(vg, nvg.rgba(255, 255, 255, 255))
        nvg.fill(vg)

        # Linear gradient
        nvg.begin_path(vg)
        nvg.rect(vg, 50, 50, 300, 150)
        paint = nvg.linear_gradient(vg, 50, 100, 350, 100, nvg.rgba(255, 0, 0, 255), nvg.rgba(0, 0, 255, 255))
        nvg.fill_paint(vg, paint)
        nvg.fill(vg)

        # Radial gradient
        nvg.begin_path(vg)
        nvg.circle(vg, 200, 350, 100)
        radial = nvg.radial_gradient(vg, 200, 350, 10, 100, nvg.rgba(255, 255, 0, 255), nvg.rgba(255, 0, 255, 0))
        nvg.fill_paint(vg, radial)
        nvg.fill(vg)

        # Box gradient
        nvg.begin_path(vg)
        nvg.rounded_rect(vg, 400, 50, 300, 150, 10)
        box_grad = nvg.box_gradient(vg, 400, 50, 300, 150, 10, 50, nvg.rgba(0, 255, 255, 255), nvg.rgba(0, 50, 50, 255))
        nvg.fill_paint(vg, box_grad)
        nvg.fill(vg)

        nvg.restore(vg)

    def _draw_text(self, vg: nvg.Context, width: float, height: float):
        """Draw text examples"""
        nvg.save(vg)

        # Background
        nvg.begin_path(vg)
        nvg.rect(vg, 0, 0, width, height)
        nvg.fill_color(vg, nvg.rgba(255, 255, 255, 255))
        nvg.fill(vg)

        if self._font_id < 0:
            nvg.restore(vg)
            return

        # Various text sizes
        sizes = [16, 24, 36, 48, 72]
        y = 50
        for size in sizes:
            nvg.font_size(vg, size)
            nvg.font_face_id(vg, self._font_id)
            nvg.fill_color(vg, nvg.rgba(0, 0, 0, 255))
            nvg.text(vg, 50, y, f"NanoVG Text - {size}pt")
            y += size + 20

        nvg.restore(vg)

    def _draw_heart(self, vg: nvg.Context, width: float, height: float):
        """Draw animated heart"""
        nvg.save(vg)

        # Background
        nvg.begin_path(vg)
        nvg.rect(vg, 0, 0, width, height)
        nvg.fill_color(vg, nvg.rgba(255, 255, 255, 255))
        nvg.fill(vg)

        # Heart shape with animation
        cx, cy = width / 2, height / 2
        t = imgui.get_time()
        scale = math.sin(t * 3) * 0.1 + 1.0
        size = min(width, height) * 0.3 * scale

        nvg.save(vg)
        nvg.translate(vg, cx, cy)
        nvg.scale(vg, size, -size)

        nvg.begin_path(vg)
        nvg.move_to(vg, 0.0, 0.4)
        nvg.bezier_to(vg, 0.0, 0.5, 0.1, 1.0, 0.5, 1.0)
        nvg.bezier_to(vg, 0.9, 1.0, 1.0, 0.7, 1.0, 0.4)
        nvg.bezier_to(vg, 1.0, 0.2, 0.75, -0.2, 0.5, -0.4)
        nvg.bezier_to(vg, 0.2, -0.65, 0.0, -0.8, 0.0, -1.0)
        nvg.bezier_to(vg, 0.0, -0.8, -0.2, -0.65, -0.5, -0.4)
        nvg.bezier_to(vg, -0.75, -0.2, -1.0, 0.2, -1.0, 0.4)
        nvg.bezier_to(vg, -1.0, 0.7, -0.9, 1.0, -0.5, 1.0)
        nvg.bezier_to(vg, -0.1, 1.0, 0.0, 0.5, 0.0, 0.4)

        paint = nvg.linear_gradient(vg, 0.0, 1.0, 0.0, -1.0, nvg.rgba(255, 0, 0, 255), nvg.rgba(255, 100, 100, 100))
        nvg.fill_paint(vg, paint)
        nvg.fill(vg)

        nvg.stroke_color(vg, nvg.rgba(200, 0, 0, 255))
        nvg.stroke_width(vg, 0.05)
        nvg.stroke(vg)

        nvg.restore(vg)
        nvg.restore(vg)

    def dispose(self) -> Result[None]:
        """Cleanup NanoVG resources"""
        if hasattr(self, '_nvg_framebuffer'):
            self._nvg_framebuffer = None
        if hasattr(self, '_vg') and self._vg:
            nvg_imgui.delete_nvg_context_hello_imgui(self._vg)
            self._vg = None
        return super().dispose()
