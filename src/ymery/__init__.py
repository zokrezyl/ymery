"""
Ymery - ImGui-based declarative UI framework
"""

# Read version from pyproject.toml (single source of truth)
try:
    from importlib.metadata import version
    __version__ = version("ymery")
except Exception:
    __version__ = "unknown"

__all__ = ["__version__"]
