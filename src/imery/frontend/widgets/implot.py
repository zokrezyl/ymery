"""
ImPlot widgets - plotting widgets following the standard Widget pattern
All widgets use "activated" parameter for children, just like composite widgets
"""

from imgui_bundle import implot, imgui
from imery.frontend.widget import Widget
from imery.decorators import widget
from imery.result import Result, Ok

import pprint


@widget
class ImplotLayer(Widget):
    """ImPlot layer widget - renders a single plot layer (line plot)"""

    def __init__(self, factory, dispatcher, namespace: str, data_bag):
        super().__init__(factory, dispatcher, namespace, data_bag)
        self._cached_buffer = None

    def _pre_render_head(self) -> Result[bool]:
        """Render plot layer - renders line plot from data"""
        # Get buffer from metadata
        metadata_res = self._data_bag.get_metadata()
        if not metadata_res:
            return Result.error("ImplotLayer: no metadata available", metadata_res)
        metadata = metadata_res.unwrapped

        # Use cached buffer if available
        if self._cached_buffer is not None:
            buffer = self._cached_buffer
        else:
            res = self._data_bag.get("buffer")
            if not res:
                # we try to get openable channel
                # Check if this is an openable channel
                res = self._data_bag.get("category")
                if not res:
                    return Result.error("ImplotLayer: _pre_render_head: 'category' field not available", res)
                category = res.unwrapped

                res = self._data_bag.get("capabilities")
                if not res:
                    return Result.error("ImplotLayer: _pre_render_head: 'capabilities' metadata not available", res)
                capabilities = res.unwrapped
                openable = capabilities.get("openable")
                if category == "audio-channel" and openable:
                    # This is an openable channel - need to call open() ONCE to get buffer
                    tree_like = self._data_bag._data_trees.get(self._data_bag._main_data_key)
                    data_path = self._data_bag._main_data_path
                    if not tree_like:
                        return Result.error("ImplotLayer: no tree_like available for opening channel")

                    # Open the channel to get the buffer
                    res = tree_like.open(data_path, {})
                    if not res:
                        return Result.error(f"ImplotLayer: failed to open channel at '{data_path}'", res)

                    buffer = res.unwrapped
                    self._cached_buffer = buffer  # Cache it!
                else:
                    return Result.error(f"ImplotLayer: _pre_render_head: invalid capabilities: {capabilities} or category: {category}")

            else:
                # Legacy: buffer directly in metadata
                buffer = metadata.get("buffer")
                if not buffer:
                    data_path = self._data_bag._main_data_path
                    return Result.error(f"ImplotLayer: no buffer in metadata and not an openable channel ({data_path})")
                self._cached_buffer = buffer  # Cache it!

        # Try to lock buffer
        if not buffer.try_lock():
            return Ok(False)  # Buffer busy, skip this frame

        try:
            # Get buffer data
            buffer_data = buffer.data
            if buffer_data is None or len(buffer_data) == 0:
                return Ok(False)  # No data to plot

            # X-axis: oldest sample at negative X, newest at 0
            xstart = -float(len(buffer_data))

            # Get label from field values
            label_res = self._data_bag.get("label")
            if not label_res:
                return Result.error("ImplotLayer: failed to get label", label_res)
            label = label_res.unwrapped

            # Plot line
            implot.plot_line(label, buffer_data, xscale=1.0, xstart=xstart)

            return Ok(False)  # Layer doesn't activate
        finally:
            buffer.unlock()


@widget
class Implot(Widget):
    """ImPlot widget - creates plot context, renders layers from activated"""

    def _pre_render_head(self) -> Result[None]:
        """Begin plot - sets _is_body_activated to render activated children"""
        res = self._data_bag.get("label")
        if not res:
            return Result.error("Implot: failed to get label", res)
        label = res.unwrapped

        self._is_body_activated = implot.begin_plot(label)
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End plot after rendering activated children - must always call end_plot"""
        if self._is_body_activated:
            implot.end_plot()
        return Ok(None)


@widget
class ImplotGroup(Widget):
    """ImPlot group widget - creates subplots context, renders plots from activated"""

    def _pre_render_head(self) -> Result[None]:
        """Begin subplots - sets _is_body_activated to render activated children"""
        res = self._data_bag.get("label")
        if not res:
            return Result.error("ImplotGroup: failed to get label", res)
        label = res.unwrapped

        res = self._data_bag.get("rows", 1)
        if not res:
            return Result.error("ImplotGroup: failed to get rows", res)
        rows = res.unwrapped

        res = self._data_bag.get("cols", 1)
        if not res:
            return Result.error("ImplotGroup: failed to get cols", res)
        cols = res.unwrapped

        res = self._data_bag.get("size", [-1, -1])
        if not res:
            return Result.error("ImplotGroup: failed to get size", res)
        size_list = res.unwrapped
        size = imgui.ImVec2(size_list[0], size_list[1])

        self._is_body_activated = implot.begin_subplots(label, rows, cols, size)
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End subplots after rendering activated children"""
        if self._is_body_activated:
            implot.end_subplots()
        return Ok(None)
