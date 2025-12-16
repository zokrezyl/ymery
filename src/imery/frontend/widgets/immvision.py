"""
ImmVision widgets - Image visualization and inspection
"""

from imgui_bundle import immvision, ImVec2, imgui, hello_imgui
from imery.frontend.widget import Widget
from imery.frontend.decorators import widget
from imery.result import Result, Ok
import numpy as np
from pathlib import Path


def _load_image(image_path: str, load_alpha: bool = False) -> np.ndarray:
    """Load image using PIL"""
    try:
        from PIL import Image
        img = Image.open(image_path)
        mode = "RGBA" if load_alpha else "RGB"
        return np.array(img.convert(mode))
    except ImportError:
        # Fallback to dummy pattern if PIL not available
        return _dummy_image(load_alpha)
    except Exception:
        return _dummy_image(load_alpha)


def _dummy_image(with_alpha: bool) -> np.ndarray:
    """Generate dummy pattern"""
    width, height = 400, 400
    x = np.linspace(-1 * np.pi, 1 * np.pi, width)
    y = np.linspace(-1 * np.pi, 1 * np.pi, height)
    X, Y = np.meshgrid(x, y)

    pattern = np.sin(X**2 + Y**2) + np.sin(3 * X + 2.5 * Y)
    normalized_pattern = (pattern - pattern.min()) / (pattern.max() - pattern.min())

    R = (np.sin(2 * np.pi * normalized_pattern) * 127 + 128).astype(np.uint8)
    G = (np.cos(3 * np.pi * normalized_pattern + np.pi / 2) * 127 + 128).astype(np.uint8)
    B = (np.sin(2 * np.pi * normalized_pattern + np.pi) * 127 + 128).astype(np.uint8)

    rgb_image = np.dstack((R, G, B))

    if not with_alpha:
        return rgb_image

    alpha = (normalized_pattern > 0.15).astype(np.uint8) * 255
    rgba_image = np.dstack((rgb_image, alpha))
    return rgba_image


@widget
class ImmvisionImageDisplay(Widget):
    """ImmVision image_display() - Simple image display"""

    def init(self) -> Result[None]:
        """Initialize immvision"""
        res = super().init()
        if not res:
            return res

        # Set color order once
        if immvision.is_color_order_undefined():
            immvision.use_rgb_color_order()

        # Load image if path provided
        self._image = None
        if isinstance(self._static, dict):
            image_path = self._static.get("image_path")
            if image_path:
                load_alpha = self._static.get("load_alpha", False)
                self._image = _load_image(image_path, load_alpha)

        if self._image is None:
            # Create default test pattern
            self._image = _dummy_image(False)

        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        """Render ImmVision image display"""
        # Get label
        label_res = self._data_bag.get("label", "Image")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "Image"
        else:
            label = str(label_res) if not isinstance(label_res, str) else label_res

        # Get size from params
        size = None
        if isinstance(self._static, dict):
            size_list = self._static.get("size")
            if size_list:
                size = (size_list[0], size_list[1])

        # Get show_options from params
        show_options = False
        if isinstance(self._static, dict):
            show_options = self._static.get("show_options", False)

        # Display image
        immvision.image_display(
            label,
            self._image,
            image_display_size=size,
            show_options_button=show_options
        )

        return Ok(None)


@widget
class ImmvisionImageDisplayResizable(Widget):
    """ImmVision image_display_resizable() - Resizable image display"""

    def init(self) -> Result[None]:
        """Initialize immvision"""
        res = super().init()
        if not res:
            return res

        # Set color order once
        if immvision.is_color_order_undefined():
            immvision.use_rgb_color_order()

        # Initialize size state
        if isinstance(self._static, dict):
            size_list = self._static.get("size", [0, int(hello_imgui.em_size(15))])
            self._image_size = ImVec2(size_list[0], size_list[1])
        else:
            self._image_size = ImVec2(0, int(hello_imgui.em_size(15)))

        # Load image if path provided
        self._image = None
        if isinstance(self._static, dict):
            image_path = self._static.get("image_path")
            if image_path:
                load_alpha = self._static.get("load_alpha", False)
                self._image = _load_image(image_path, load_alpha)

        if self._image is None:
            # Create default test pattern
            self._image = _dummy_image(False)

        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        """Render ImmVision resizable image display"""
        # Get label
        label_res = self._data_bag.get("label", "Resizable Image")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "Resizable Image"
        else:
            label = str(label_res) if not isinstance(label_res, str) else label_res

        # Display resizable image
        immvision.image_display_resizable(
            label,
            self._image,
            size=self._image_size
        )

        return Ok(None)


@widget
class ImmvisionImage(Widget):
    """ImmVision image() - Full-featured image inspector with zoom/pan"""

    def init(self) -> Result[None]:
        """Initialize immvision"""
        res = super().init()
        if not res:
            return res

        # Set color order once
        if immvision.is_color_order_undefined():
            immvision.use_rgb_color_order()

        # Create image params
        self._image_params = immvision.ImageParams()

        # Load image if path provided
        self._image = None
        if isinstance(self._static, dict):
            image_path = self._static.get("image_path")
            if image_path:
                load_alpha = self._static.get("load_alpha", False)
                self._image = _load_image(image_path, load_alpha)

            # Set display size from params
            size_list = self._static.get("size")
            if size_list:
                display_size = int(hello_imgui.em_size(size_list[0]))
                self._image_params.image_display_size = (display_size, display_size)

        if self._image is None:
            # Create default test pattern with alpha
            self._image = _dummy_image(True)

        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        """Render ImmVision full image inspector"""
        # Get label
        label_res = self._data_bag.get("label", "Image Inspector")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "Image Inspector"
        else:
            label = str(label_res) if not isinstance(label_res, str) else label_res

        # Display image with full inspector
        immvision.image(label, self._image, self._image_params)

        return Ok(None)
