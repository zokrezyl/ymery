"""
TextEditor widgets - Code editor with syntax highlighting
"""

from imgui_bundle import imgui, imgui_color_text_edit as ed
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok


@widget
class TextEditor(Widget):
    """TextEditor widget - Code editor with syntax highlighting"""

    def init(self) -> Result[None]:
        """Initialize text editor"""
        res = super().init()
        if not res:
            return res

        # Create text editor instance
        self._editor = ed.TextEditor()
        self._editor.set_palette(ed.TextEditor.PaletteId.dark)

        return Ok(None)

    def _pre_render_head(self) -> Result[None]:
        """Render text editor"""
        text_res = self._data_bag.get("label")
        if not text_res:
            return Result.error(f"TextEditor: failed to get text", text_res)

        text = text_res.unwrapped
        if not isinstance(text, str):
            text = ""

        # Set text if changed from outside
        if self._editor.get_text() != text:
            self._editor.set_text(text)

        # Get language from params
        language = "python"
        res = self._handle_error(self._data_bag.get("language", language))
        if res:
            language = res.unwrapped

        # Set language definition
        lang_id = getattr(ed.TextEditor.LanguageDefinitionId, language, None)
        if not lang_id:
            return Result.error(f"TextEditor: unknown language '{language}'")
        self._editor.set_language_definition(lang_id)

        # Render the editor
        self._editor.render(f"##editor_{self.uid}")

        # Update data if text changed
        new_text = self._editor.get_text()
        if new_text != text:
            set_res = self._data_bag.set("label", new_text)
            if not set_res:
                return Result.error(f"TextEditor: failed to set text", set_res)

        return Ok(None)
