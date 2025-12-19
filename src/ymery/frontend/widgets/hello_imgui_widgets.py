"""
HelloImGui-specific widgets for menu bar integration
"""

from ymery.frontend.composite import Composite
from ymery.decorators import widget


@widget
class HelloImguiMenu(Composite):
    """HelloImGui menu bar contents widget

    Renders children inside HelloImGui's menu bar context.
    HelloImGui handles begin_main_menu_bar() / end_main_menu_bar() automatically.
    This widget just renders its Menu children.
    """
    pass  # No overrides needed - Composite handles rendering children


@widget
class HelloImguiAppMenuItems(Composite):
    """HelloImGui app menu items widget

    Adds custom items to the HelloImGui App menu.
    Children should be menu-item widgets.
    """
    pass  # No overrides needed - Composite handles rendering children
