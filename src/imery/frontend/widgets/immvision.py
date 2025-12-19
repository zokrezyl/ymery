"""
ImmVision widgets - Image visualization and inspection
"""

from imgui_bundle import immvision, ImVec2, imgui, hello_imgui
from imery.frontend.widget import Widget
from imery.decorators import widget
from imery.result import Result, Ok
import numpy as np
from pathlib import Path


def _resolve_image_path(image_path: str) -> str:
    """Resolve image path - check relative to package if not found directly."""
    path = Path(image_path)

    # Try direct path first
    if path.exists():
        return image_path

    # Try relative to imery package
    import imery
    package_dir = Path(imery.__file__).parent
    package_path = package_dir / image_path
    if package_path.exists():
        return str(package_path)

    return image_path  # Return original, let caller handle error


def _load_image(image_path: str, load_alpha: bool = False) -> np.ndarray:
    """Load image using PIL"""
    resolved_path = _resolve_image_path(image_path)
    try:
        from PIL import Image
        img = Image.open(resolved_path)
        mode = "RGBA" if load_alpha else "RGB"
        return np.array(img.convert(mode))
    except ImportError:
        print(f"Warning: PIL not available, using dummy image for {image_path}")
        return _dummy_image(load_alpha)
    except FileNotFoundError:
        print(f"Warning: Image not found: {image_path} (resolved: {resolved_path})")
        return _dummy_image(load_alpha)
    except Exception as e:
        print(f"Warning: Failed to load image {image_path}: {e}")
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
        image_path = None
        res = self._handle_error(self._data_bag.get("image_path", image_path))
        if res:
            image_path = res.unwrapped
        if image_path:
            load_alpha = False
            res = self._handle_error(self._data_bag.get("load_alpha", load_alpha))
            if res:
                load_alpha = res.unwrapped
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
        size_list = None
        res = self._handle_error(self._data_bag.get("size", size_list))
        if res and res.unwrapped:
            size_list = res.unwrapped
            size = (size_list[0], size_list[1])

        # Get show_options from params
        show_options = False
        res = self._handle_error(self._data_bag.get("show_options", show_options))
        if res:
            show_options = res.unwrapped

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
        size_list = [0, int(hello_imgui.em_size(15))]
        res = self._handle_error(self._data_bag.get("size", size_list))
        if res:
            size_list = res.unwrapped
        self._image_size = ImVec2(size_list[0], size_list[1])

        # Load image if path provided
        self._image = None
        image_path = None
        res = self._handle_error(self._data_bag.get("image_path", image_path))
        if res:
            image_path = res.unwrapped
        if image_path:
            load_alpha = False
            res = self._handle_error(self._data_bag.get("load_alpha", load_alpha))
            if res:
                load_alpha = res.unwrapped
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
        image_path = None
        res = self._handle_error(self._data_bag.get("image_path", image_path))
        if res:
            image_path = res.unwrapped
        if image_path:
            load_alpha = False
            res = self._handle_error(self._data_bag.get("load_alpha", load_alpha))
            if res:
                load_alpha = res.unwrapped
            self._image = _load_image(image_path, load_alpha)

        # Set display size from params
        size_list = None
        res = self._handle_error(self._data_bag.get("size", size_list))
        if res and res.unwrapped:
            size_list = res.unwrapped
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
