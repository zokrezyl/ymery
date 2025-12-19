"""
CoolBar widgets - Dock-like cool bar using im_cool_bar
"""

from imgui_bundle import imgui, im_cool_bar, hello_imgui, ImVec2, immapp
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok


@widget
class CoolBar(Widget):
    """CoolBar widget - Dock-like cool bar"""

    def _pre_render_head(self) -> Result[None]:
        """Render cool bar"""
        # Get label
        label_res = self._data_bag.get("label", "CoolBar")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "CoolBar"
        else:
            label = str(label_res) if not isinstance(label_res, str) else label_res

        # Get params
        anchor_x = 0.5
        res = self._handle_error(self._data_bag.get("anchor_x", anchor_x))
        if res:
            anchor_x = res.unwrapped

        anchor_y = 0.07
        res = self._handle_error(self._data_bag.get("anchor_y", anchor_y))
        if res:
            anchor_y = res.unwrapped

        horizontal = True
        res = self._handle_error(self._data_bag.get("horizontal", horizontal))
        if res:
            horizontal = res.unwrapped

        # Create config
        cool_bar_config = im_cool_bar.ImCoolBarConfig()
        cool_bar_config.anchor = ImVec2(anchor_x, anchor_y)

        # Get flags
        flags = im_cool_bar.ImCoolBarFlags_.horizontal.value if horizontal else 0

        # Begin cool bar
        imgui_id = f"##{label}_{self.uid}"
        if im_cool_bar.begin_cool_bar(imgui_id, flags, cool_bar_config):
            # Render body items
            self._is_body_activated = True
        else:
            self._is_body_activated = False

        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End cool bar"""
        if self._is_body_activated:
            im_cool_bar.end_cool_bar()
        return Ok(None)


@widget
class CoolBarItem(Widget):
    """CoolBarItem widget - Item in cool bar"""

    def _pre_render_head(self) -> Result[None]:
        """Render cool bar item"""
        # Get label
        label_res = self._data_bag.get("label", "Item")
        if isinstance(label_res, Result):
            label = label_res.unwrapped if label_res else "Item"
        else:
            label = str(label_res) if not isinstance(label_res, str) else label_res

        # Get image path from params
        # Use an image that exists in imgui_bundle assets by default
        image_path = "images/world.png"
        res = self._handle_error(self._data_bag.get("image", image_path))
        if res:
            image_path = res.unwrapped

        # Begin cool bar item
        if im_cool_bar.cool_bar_item():
            w = im_cool_bar.get_cool_bar_item_width()

            # Display image
            hello_imgui.image_from_asset(image_path, ImVec2(w, w))
            clicked = imgui.is_item_hovered() and imgui.is_mouse_clicked(0)

            # Add label on image
            top_left_corner = imgui.get_item_rect_min()
            text_pos = ImVec2(
                top_left_corner.x + immapp.em_size(1.0),
                top_left_corner.y + immapp.em_size(1.0),
            )
            imgui.get_window_draw_list().add_text(text_pos, 0xFFFFFFFF, label)

            if clicked:
                # Handle click - could trigger data change
                pass

        return Ok(None)
