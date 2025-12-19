"""
Matplotlib widgets - Display matplotlib figures in ImGui
Uses Agg backend for headless rendering, displays via immvision
"""

import numpy as np
from imgui_bundle import imgui, immvision, ImVec2
from imery.frontend.widget import Widget
from imery.decorators import widget
from imery.result import Result, Ok


def _ensure_agg_backend():
    """Ensure matplotlib uses Agg backend for headless rendering."""
    import matplotlib
    if matplotlib.rcParams['backend'].lower() != 'agg':
        matplotlib.use('Agg')


def _fig_to_image_nocache(figure) -> np.ndarray:
    """
    Convert a matplotlib figure to an RGBA numpy array without caching.

    Parameters:
        figure: matplotlib.figure.Figure to convert

    Returns:
        numpy.ndarray: RGBA image as uint8 array
    """
    import matplotlib.pyplot as plt

    figure.canvas.draw()
    w, h = figure.canvas.get_width_height()
    buf = np.frombuffer(figure.canvas.buffer_rgba(), dtype=np.uint8)

    try:
        image = buf.reshape((h, w, 4)).copy()
        plt.close(figure)
        return image
    except ValueError as e:
        print(f"Warning: matplotlib figure conversion failed: {e}")
        plt.close(figure)
        return np.zeros((100, 100, 4), dtype=np.uint8)


@widget
class MatplotlibFig(Widget):
    """Display a matplotlib figure

    Can either receive a figure object or create one from YAML plot config.

    YAML usage:
        matplotlib-fig:
            label: "My Plot"
            size: [400, 300]
            resizable: true
            refresh: false
    """

    def init(self) -> Result[None]:
        res = super().init()
        if not res:
            return res

        _ensure_agg_backend()

        # Initialize size state
        size_list = [400, 300]
        res = self._handle_error(self._data_bag.get("size", size_list))
        if res:
            size_list = res.unwrapped
        self._size = ImVec2(size_list[0], size_list[1])

        # Store figure reference
        self._figure = None

        return Ok(None)

    def set_figure(self, figure):
        """Set the matplotlib figure to display."""
        self._figure = figure

    def _pre_render_head(self) -> Result[None]:
        """Render matplotlib figure"""
        # Get label
        label = "matplotlib"
        res = self._handle_error(self._data_bag.get("label", label))
        if res:
            label = res.unwrapped

        # Get refresh flag
        refresh = False
        res = self._handle_error(self._data_bag.get("refresh", refresh))
        if res:
            refresh = res.unwrapped

        # Get resizable flag
        resizable = True
        res = self._handle_error(self._data_bag.get("resizable", resizable))
        if res:
            resizable = res.unwrapped

        # Get show_options flag
        show_options = False
        res = self._handle_error(self._data_bag.get("show_options", show_options))
        if res:
            show_options = res.unwrapped

        if self._figure is None:
            imgui.text(f"{label}: No figure set")
            return Ok(None)

        # Convert figure to image
        if self._image is None or refresh:
            self._image = _fig_to_image_nocache(self._figure)

        # Display using immvision
        immvision.push_color_order_rgb()
        if resizable:
            immvision.image_display_resizable(
                label, self._image, size=self._size
            )
        else:
            immvision.image_display(
                label, self._image,
                image_display_size=(int(self._size.x), int(self._size.y)),
                show_options_button=show_options
            )
        immvision.pop_color_order()

        return Ok(None)


@widget
class MatplotlibLinePlot(Widget):
    """Simple line plot widget using matplotlib

    Creates a line plot from data arrays provided in YAML or programmatically.

    YAML usage:
        matplotlib-line-plot:
            label: "Signal"
            title: "My Signal Plot"
            xlabel: "Time"
            ylabel: "Amplitude"
            size: [400, 300]
            data:
                x: [0, 1, 2, 3, 4]
                y: [0, 1, 4, 9, 16]
    """

    def init(self) -> Result[None]:
        res = super().init()
        if not res:
            return res

        _ensure_agg_backend()

        # Initialize size
        size_list = [400, 300]
        res = self._handle_error(self._data_bag.get("size", size_list))
        if res:
            size_list = res.unwrapped
        self._size = ImVec2(size_list[0], size_list[1])

        # Cache
        self._image = None
        self._last_data_hash = None

        return Ok(None)

    def _create_figure(self, x_data, y_data, title, xlabel, ylabel):
        """Create matplotlib figure with line plot."""
        import matplotlib.pyplot as plt

        # Calculate figure size in inches (assuming 100 dpi)
        dpi = 100
        figsize = (self._size.x / dpi, self._size.y / dpi)

        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        ax.plot(x_data, y_data)

        if title:
            ax.set_title(title)
        if xlabel:
            ax.set_xlabel(xlabel)
        if ylabel:
            ax.set_ylabel(ylabel)

        ax.grid(True, alpha=0.3)
        fig.tight_layout()

        return fig

    def _pre_render_head(self) -> Result[None]:
        """Render line plot"""
        # Get label
        label = "line_plot"
        res = self._handle_error(self._data_bag.get("label", label))
        if res:
            label = res.unwrapped

        # Get plot metadata
        title = ""
        res = self._handle_error(self._data_bag.get("title", title))
        if res:
            title = res.unwrapped

        xlabel = ""
        res = self._handle_error(self._data_bag.get("xlabel", xlabel))
        if res:
            xlabel = res.unwrapped

        ylabel = ""
        res = self._handle_error(self._data_bag.get("ylabel", ylabel))
        if res:
            ylabel = res.unwrapped

        # Get data
        data = {}
        res = self._handle_error(self._data_bag.get("data", data))
        if res:
            data = res.unwrapped

        x_data = data.get("x", [])
        y_data = data.get("y", [])

        if not y_data:
            imgui.text(f"{label}: No data")
            return Ok(None)

        # Generate x if not provided
        if not x_data:
            x_data = list(range(len(y_data)))

        # Check if data changed
        data_hash = hash((tuple(x_data), tuple(y_data), title, xlabel, ylabel))
        if data_hash != self._last_data_hash:
            fig = self._create_figure(x_data, y_data, title, xlabel, ylabel)
            self._image = _fig_to_image_nocache(fig)
            self._last_data_hash = data_hash

        if self._image is not None:
            immvision.push_color_order_rgb()
            immvision.image_display_resizable(label, self._image, size=self._size)
            immvision.pop_color_order()

        return Ok(None)


@widget
class Matplotlib(Widget):
    """Interactive matplotlib widget - reads parameters from data_bag

    Parameters are controlled via separate slider widgets in YAML.

    YAML usage:
        matplotlib:
            size: [500, 400]
            plot_type: "line"  # line, scatter, bar, multi
            points: 50
            amplitude: 1.0
            frequency: 1.0
            noise: 0.1
    """

    def init(self) -> Result[None]:
        res = super().init()
        if not res:
            return res

        _ensure_agg_backend()

        return Ok(None)

    def _create_demo_figure(self, plot_type, num_points, amplitude, frequency, noise_level, size):
        """Create demo figure based on parameters."""
        import matplotlib.pyplot as plt

        dpi = 100
        figsize = (size[0] / dpi, size[1] / dpi)
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)

        x = np.linspace(0, 4 * np.pi, num_points)
        noise = np.random.randn(num_points) * noise_level

        if plot_type == "line":
            y = amplitude * np.sin(frequency * x) + noise
            ax.plot(x, y, 'b-', linewidth=2)
            ax.set_title("Line Plot")
        elif plot_type == "scatter":
            y = amplitude * np.sin(frequency * x) + noise
            ax.scatter(x, y, c=y, cmap='viridis', s=20)
            ax.set_title("Scatter Plot")
        elif plot_type == "bar":
            x_bar = np.arange(min(10, num_points))
            y_bar = amplitude * np.sin(frequency * x_bar * 0.5) + noise[:len(x_bar)]
            ax.bar(x_bar, y_bar, color='steelblue')
            ax.set_title("Bar Chart")
        elif plot_type == "multi":
            for i in range(1, 4):
                y = amplitude * np.sin(frequency * i * x) / i
                ax.plot(x, y, label=f'sin({i}x)/{i}')
            ax.legend()
            ax.set_title("Multiple Sine Waves")

        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        ax.grid(True, alpha=0.3)
        fig.tight_layout()

        return fig

    def _pre_render_head(self) -> Result[None]:
        """Render plot based on data_bag parameters"""
        # Read size
        size = [500, 400]
        res = self._handle_error(self._data_bag.get("size", size))
        if res:
            size = res.unwrapped

        # Read parameters from data_bag
        plot_type = "line"
        res = self._handle_error(self._data_bag.get("plot_type", plot_type))
        if res:
            plot_type = res.unwrapped

        num_points = 50
        res = self._handle_error(self._data_bag.get("points", num_points))
        if res:
            num_points = int(res.unwrapped)

        amplitude = 1.0
        res = self._handle_error(self._data_bag.get("amplitude", amplitude))
        if res:
            amplitude = float(res.unwrapped)

        frequency = 1.0
        res = self._handle_error(self._data_bag.get("frequency", frequency))
        if res:
            frequency = float(res.unwrapped)

        noise_level = 0.1
        res = self._handle_error(self._data_bag.get("noise", noise_level))
        if res:
            noise_level = float(res.unwrapped)

        # Create figure and convert to image - no caching
        fig = self._create_demo_figure(plot_type, num_points, amplitude, frequency, noise_level, size)
        image = _fig_to_image_nocache(fig)

        # Display - clear texture cache to force refresh
        immvision.clear_texture_cache()
        immvision.push_color_order_rgb()
        immvision.image_display_resizable("matplotlib_demo", image, size=ImVec2(size[0], size[1]))
        immvision.pop_color_order()

        return Ok(None)
