"""
TextEditor widgets - Code editor with syntax highlighting
"""

from imgui_bundle import imgui, imgui_color_text_edit as ed
from imery.frontend.widget import Widget
from imery.frontend.decorators import widget
from imery.result import Result, Ok


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
        if not self._data_path:
            return Result.error("TextEditor requires path (id)")

        # Get text from data
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
        if isinstance(self._static, dict):
            language = self._static.get("language", "python")

            # Set language definition
            if language == "python":
                self._editor.set_language_definition(ed.TextEditor.LanguageDefinitionId.python)
            elif language == "cpp" or language == "c++":
                self._editor.set_language_definition(ed.TextEditor.LanguageDefinitionId.cpp)
            elif language == "c":
                self._editor.set_language_definition(ed.TextEditor.LanguageDefinitionId.c)
            elif language == "sql":
                self._editor.set_language_definition(ed.TextEditor.LanguageDefinitionId.sql)
            elif language == "hlsl":
                self._editor.set_language_definition(ed.TextEditor.LanguageDefinitionId.hlsl)
            elif language == "lua":
                self._editor.set_language_definition(ed.TextEditor.LanguageDefinitionId.lua)

        # Render the editor
        self._editor.render(f"##editor_{self.uid}")

        # Update data if text changed
        new_text = self._editor.get_text()
        if new_text != text:
            set_res = self._data_bag.set("label", new_text)
            if not set_res:
                return Result.error(f"TextEditor: failed to set text", set_res)

        return Ok(None)
