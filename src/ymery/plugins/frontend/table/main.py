"""
Table widgets - table layout widgets following the standard Widget pattern
All widgets use "activated" parameter for children, just like composite widgets
"""

from imgui_bundle import imgui
from ymery.frontend.widget import Widget
from ymery.decorators import widget
from ymery.result import Result, Ok

@widget
class Table(Widget):
    """Table widget - creates table context, renders rows from activated"""

    def _pre_render_head(self) -> Result[None]:
        """Begin table - sets _is_body_activated to render activated children"""
        # Get label from field values
        label_res = self._data_bag.get("label")
        if not label_res:
            return Result.error("Table: failed to get label", label_res)
        label = label_res.unwrapped

        # Get number of columns from params
        num_columns = 1
        res = self._handle_error(self._data_bag.get("columns", num_columns))
        if res:
            num_columns = res.unwrapped

        # Get flags from params
        flags = imgui.TableFlags_.none
        flags_list = []
        res = self._handle_error(self._data_bag.get("flags", flags_list))
        if res:
            flags_list = res.unwrapped
        for flag_name in flags_list:
            flag_attr = flag_name.replace("-", "_")
            if hasattr(imgui.TableFlags_, flag_attr):
                flags |= getattr(imgui.TableFlags_, flag_attr)

        # Begin table and set _is_body_activated
        self._is_body_activated = imgui.begin_table(label, num_columns, flags)
        return Ok(None)

    def _post_render_head(self) -> Result[None]:
        """End table after rendering activated children - only if table was opened"""
        if self._is_body_activated:
            imgui.end_table()
        return Ok(None)


@widget
class Row(Widget):
    """Row widget - advances to next table row, renders columns from activated"""

    def _pre_render_head(self) -> Result[None]:
        """Advance to next row - sets _is_body_activated to render activated children"""
        # Get min height from params
        min_height = 0.0
        res = self._handle_error(self._data_bag.get("min-height", min_height))
        if res:
            min_height = res.unwrapped

        # Get flags from params
        flags = imgui.TableRowFlags_.none
        flags_list = []
        res = self._handle_error(self._data_bag.get("flags", flags_list))
        if res:
            flags_list = res.unwrapped
        for flag_name in flags_list:
            flag_attr = flag_name.replace("-", "_")
            if hasattr(imgui.TableRowFlags_, flag_attr):
                flags |= getattr(imgui.TableRowFlags_, flag_attr)

        # Call table_next_row
        imgui.table_next_row(flags, min_height)
        self._is_body_activated = True  # Always render activated children
        return Ok(None)


@widget
class Column(Widget):
    """Column widget - advances to next table column, renders content from activated"""

    def _pre_render_head(self) -> Result[None]:
        """Advance to next column - sets _is_body_activated to render activated children"""
        # Call table_next_column
        imgui.table_next_column()
        self._is_body_activated = True  # Always render activated children
        return Ok(None)
