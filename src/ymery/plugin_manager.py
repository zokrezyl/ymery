from ymery.backend.types import TreeLike
from ymery.types import DataPath, Object
from ymery.decorators import _pending_device_managers, _pending_devices, _pending_tree_likes, _pending_widgets

from typing import Optional, Dict, Any, Union
from ymery.result import Result, Ok
from pathlib import Path

from ymery.stringcase import spinalcase
from ymery.utils import call_by_path


import importlib.util
import sys


class PluginManager(TreeLike, Object):
    def __init__(self, plugins_path: Optional[str] = None):
        super().__init__()
        self._plugins_path = plugins_path
        self._plugins = None

    def init(self) -> Result[None]:
        # TODO: validate _plugin_path
        # print("PluginManager: init")
        # return self._ensure_plugins_loaded()
        return Ok(None)

    def get_children_names(self, path: DataPath) -> Result[list]:
        # print(f"PluginManager: get_children_names: {path}, {len(path)}")
        res = self._ensure_plugins_loaded()
        if not res:
            return Result.error("PluginManager: error loading plugins", res)

        if path == "/":
            return Ok(list(self._plugins.keys()))

        if len(path) == 1:
            category = path[0]
            if category not in self._plugins:
                return Result.error(f"PluginManager: get_children_names: category '{category}' not found")
            return Ok(list(self._plugins[category].keys()))

        return Result.error(f"PluginManager: get_children_names: path too deep: {path}")


    def get_metadata(self, path: DataPath) -> Result[Dict[str, Any]]:
        res = self._ensure_plugins_loaded()
        if not res:
            return Result.error("PluginManager: error loading plugins", res)

        if path == "/":
            return Ok({"name": "plugins"})

        if len(path) == 1:
            category = path[0]
            if category not in self._plugins:
                return Result.error(f"PluginManager: get_metadata: category '{category}' not found")
            return Ok({"name": category})

        if len(path) == 2:
            category = path[0]
            registered_name = path[1]
            if category not in self._plugins:
                return Result.error(f"PluginManager: get_metadata: category '{category}' not found")
            if registered_name not in self._plugins[category]:
                return Result.error(f"PluginManager: get_metadata: '{registered_name}' not found in '{category}'")
            cls = self._plugins[category][registered_name]
            return Ok({
                "class-name": cls.__name__,
                "registered-name": registered_name,
                "class": cls
            })

        return Result.error(f"PluginManager: get_metadata: path too deep: {path}")

    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        """Get metadata keys using existing get_metadata"""
        res = self.get_metadata(path)
        if not res:
            return Result.error(f"PluginManager: failed to get metadata for {path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            return Ok(list(metadata.keys()))
        return Result.error(f"PluginManager: metadata is not a dict at {path}")

    def get(self, path: DataPath) -> Result:
        """Get metadata value - last component of path is the key"""
        node_path = path.dirname()
        key = path.filename()

        res = self.get_metadata(node_path)
        if not res:
            return Result.error(f"PluginManager: failed to get metadata for {node_path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            if key in metadata:
                return Ok(metadata[key])
            return Result.error(f"PluginManager: key '{key}' not found in metadata at {node_path}")
        return Result.error(f"PluginManager: metadata is not a dict at {node_path}")

    def set(self, path: DataPath, value) -> Result[None]:
        """Set not implemented"""
        return Result.error("PluginManager: set: not implemented")

    def add_child(self, path: DataPath, value0) -> Result[None]:
        return Result.error("PluginManager: add-child: not implemented")

    def open(self, path: DataPath, *args, **kwargs) -> Result:
        """Delegate open to the appropriate provider manager"""
        res = self._ensure_plugins_loaded()
        if not res:
            return Result.error("PluginManager: error loading plugins", res)
        return call_by_path(self._plugins, path, "open", *args, *kwargs)

    def configure(self, path: DataPath, params: Dict) -> Result[None]:
        """Delegate reconfig_asset to the appropriate provider manager"""
        res = self._ensure_plugins_loaded()
        if not res:
            return Result.error("PluginManager: error loading plugins", res)
        return call_by_path(self._plugins, path, "configure", params)

    def close(self, path: DataPath) -> Result[None]:
        """Delegate close to the appropriate provider manager"""
        res = self._ensure_plugins_loaded()
        if not res:
            return Result.error("PluginManager: error loading plugins", res)
        return call_by_path(self._plugins, path, "close", {})

    def _ensure_plugins_loaded(self) -> Result[None]:
        """Lazy load all provider plugins."""
        # log("XXXXXXXXX ensure plugins loaded")
        if self._plugins:
            return Ok(None)
        self._plugins = {}

        # Build list of provider directories from colon-separated path
        plugin_dirs = []
        if self._plugins_path:
            # Parse colon-separated paths
            for path_str in self._plugins_path.split(':'):
                path_str = path_str.strip()
                if path_str:
                    plugin_dirs.append(Path(path_str))
        else:
            return Result.error("plugin path not available")

        # Scan each provider directory
        for plugins_dir in plugin_dirs:
            if not plugins_dir.exists():
                print(f"{plugins_dir} does not exist")
                continue

            # Scan each subdirectory in plugins_dir
            for plugin_dir in plugins_dir.iterdir():
                if not plugin_dir.is_dir():
                    print(f"{plugin_dir} not directory")
                    continue

                main_py = plugin_dir / "main.py"
                if not main_py.exists():
                    print(f"{main_py} does not exist")
                    continue

                plugin_name = plugin_dir.name

                try:
                    print(f"loading.. {main_py}")
                    # Load the module dynamically
                    spec = importlib.util.spec_from_file_location(
                        f"ymery.plugins.{plugin_name}.main",
                        main_py
                    )
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[spec.name] = module
                    spec.loader.exec_module(module)

                except ModuleNotFoundError as e:
                    return Result.error(f"PluginManager: _ensure_plugins_loaded: Could not load {main_py}", e)

        print("all plugin files loaded successfully")
        print("processing widget classes...")
        self._plugins["widget"] = dict(_pending_widgets)
        for name, cls in _pending_widgets.items():
            print(f"registering widget class: {cls.__name__} as {name}")

        print("processing device manager classes...")
        self._plugins["device-manager"] = dict(_pending_device_managers)
        for name, cls in _pending_device_managers.items():
            print(f"registering device manager class: {cls.__name__} as {name}")

        print("processing device classes...")
        self._plugins["device"] = dict(_pending_devices)
        for name, cls in _pending_devices.items():
            print(f"registering device class: {cls.__name__} as {name}")

        print("processing tree-like classes...")
        self._plugins["tree-like"] = dict(_pending_tree_likes)
        for name, cls in _pending_tree_likes.items():
            print(f"registering tree-like class: {cls.__name__} as {name}")

        return Ok(None)

    def dispose(self) -> Result[None]:
        return Ok(None)
    
    def as_tree(self, data_path: DataPath = None, depth: int = 0) -> Result[Union[dict]]:
        pass

    def get_registered(self, whatever):
        print("get_registered")
        return self._ensure_plugins_loaded()
        pass
    
