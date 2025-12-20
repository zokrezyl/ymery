"""
Markdown widgets - Markdown rendering with imgui_md
"""

from imgui_bundle import imgui_md
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok


@widget
class Markdown(Widget):
    """Markdown widget - Renders markdown text"""

    def _pre_render_head(self) -> Result[None]:
        """Render markdown"""
        # Get markdown text from label field
        text_res = self._data_bag.get("label", "")
        if isinstance(text_res, Result):
            text = text_res.unwrapped if text_res else ""
        else:
            text = text_res

        if not isinstance(text, str):
            text = str(text)

        # Render the markdown
        imgui_md.render(text)

        return Ok(None)


@widget
class MarkdownUnindented(Widget):
    """MarkdownUnindented widget - Renders unindented markdown text"""

    def _pre_render_head(self) -> Result[None]:
        """Render unindented markdown"""
        # Get markdown text from label field
        text_res = self._data_bag.get("label", "")
        if isinstance(text_res, Result):
            text = text_res.unwrapped if text_res else ""
        else:
            text = text_res

        if not isinstance(text, str):
            text = str(text)

        # Render the markdown unindented
        imgui_md.render_unindented(text)

        return Ok(None)
