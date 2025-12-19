"""
NodeEditor widgets - Node-based visual programming
"""

from imgui_bundle import imgui, imgui_node_editor as ed, ImVec2
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok


@widget
class NodeEditor(Widget):
    """NodeEditor widget - Node graph editor"""

    def init(self) -> Result[None]:
        """Initialize node editor context"""
        res = super().init()
        if not res:
            return res

        # Create node editor context
        self._editor_context = ed.create_editor()
        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        """Begin node editor"""
        label_res = self._data_bag.get("label", "Node Editor")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "Node Editor"
        else:
            label = "Node Editor"

        # Get size from params
        size_list = [800, 600]
        res = self._handle_error(self._data_bag.get("size", size_list))
        if res:
            size_list = res.unwrapped
        size = ImVec2(size_list[0], size_list[1])

        # Set context and begin editor
        ed.set_current_editor(self._editor_context)
        ed.begin(label, size)

        self._is_body_activated = True

        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End node editor"""
        ed.end()
        return Ok(None)

    def dispose(self) -> Result[None]:
        """Cleanup node editor context"""
        if hasattr(self, '_editor_context') and self._editor_context:
            ed.destroy_editor(self._editor_context)
            self._editor_context = None
        return super().dispose()


@widget
class Node(Widget):
    """Node widget - Single node in editor"""

    def _pre_render_head(self) -> Result[None]:
        """Render node"""
        label_res = self._data_bag.get("label", "Node")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "Node"
        else:
            label = label_res

        # Create unique node ID
        node_id = ed.NodeId(hash(f"node_{self.uid}") & 0x7FFFFFFF)

        # Begin node
        ed.begin_node(node_id)
        imgui.text(label)

        self._is_body_activated = True
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End node"""
        ed.end_node()
        return Ok(None)


@widget
class NodePin(Widget):
    """NodePin widget - Input/output pin"""

    def _prepare_render(self) -> Result[None]:
        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        """Render pin"""
        label_res = self._data_bag.get("label", "Pin")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "Pin"
        else:
            label = label_res

        pin_type = "input"
        res = self._handle_error(self._data_bag.get("type", pin_type))
        if res:
            pin_type = res.unwrapped
        kind = ed.PinKind.input
        if pin_type == "output":
            kind = ed.PinKind.output

        # Create unique pin ID
        pin_id = ed.PinId(hash(f"pin_{self.uid}") & 0x7FFFFFFF)

        # Begin pin
        ed.begin_pin(pin_id, kind)
        imgui.text(label)
        ed.end_pin()

        return Ok(None)
