from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
import yaml
from pathlib import Path
from ymery.result import Result, Ok, Err
from ymery.types import Object


class Visual(Object):
    """
    Abstract base class for all the visuals used in ymery
    This enforces correct lifecycle of UI objects considering:
    -> resource managament needs
    -> IMGUI specific flow
    """
    @abstractmethod
    def init(self) -> Result[None]:
        """
        Abstract method that is doing initialization
        called only once during the lifetime
        Implementations should implement here "business" logic especially logic that may throw exception
        The __init__ should pass the necessary dependencies and init should use them

        Returns:
            Result[None]: Ok(None) on success, Err(error) on failure
        """
        pass

    @abstractmethod
    def render(self) -> Result[bool]:
        """
        should implement the imgui specific rendering

        Returns:
            Result[bool]: Ok(bool) on success indicating if render should continue, Err(error) on failure

        Note: Should catch known exceptions and return Err(), never raise
        """
        pass

    @abstractmethod
    def dispose(self) -> Result[None]:
        """
        should implement the resource freeing related logic

        Returns:
            Result[None]: Ok(None) on success, Err(error) on failure
        """
        pass



class Pane(Visual):
    """
    A pane is a top-level visual container (e.g., resizable panel)
    """
    pass


class View(Visual):
    """
    Abstract base class for visual views
    Such a view may be used wrapped by a dialog or by popup
    """
    pass


class ModalDialog(Visual):
    """
    Abstract base class for modal visual dialogs
    """
    pass


class Popup(Visual):
    """
    Abstract base class for popups
    A popup may wrap a view
    """
    pass

class Window(Visual):
    pass


class PlottingLayer:
    pass
