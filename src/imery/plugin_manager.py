from imery.backend.types import TreeLike
from imery.types import DataPath, Object
from imery.decorators import _pending_device_managers, _pending_devices

from typing import Optional, Dict, Any, Union
from imery.result import Result, Ok
from pathlib import Path

import importlib.util
import sys

def call_by_path(obj, path: DataPath, what, params: Dict = None) -> Result[Object]:

    if what == "children-names":
        method_name = "get_children_names"
        attribute_name = "children"
    elif what == "metadata":
        method_name = "get_metadata"
        attribute_name = "metadata"
    elif what == "open":
        method_name = "open"
        attribute_name = "open"
    elif what == "configure":
        method_name = "configure"
        attribute_name = "configure"
    elif what == "close":
        method_name = "close"
        attribute_name = "close"
    elif what in ["register_opened_asset", "unregister_opened_asset"]:
        method_name = what
        attribute_name = what
    else:
        return Result.error(f"cannot handle {what}")

    # Check if obj is a dict (tree node) - if not, must have seed
    if not isinstance(obj, dict):
        return Result.error("call_by_path: object is not a dictionary and has no seed")

    seed_instance = obj.get("seed-instance")
    if seed_instance:
        # we do not cache, providers cache
        method = getattr(seed_instance, method_name)
        if what in ["open", "configure", "close"] and params is not None:
            return method(path, params)
        elif what in ["register_opened_asset", "unregister_opened_asset"] and params is not None:
            # register_opened_asset(relative_path, asset, metadata)
            # path here is /opened/providers, but we need to pass the relative path from params
            return method(params.get("path"), params.get("asset"), params.get("metadata"))
        else:
            return method(path)

    seed_class = obj.get("seed-class")
    if seed_class:
        constructor_args = obj.get("seed-constructor-args")
        if constructor_args:
            # Convert hyphenated keys to underscores for Python kwargs
            python_args = {k.replace('-', '_'): v for k, v in constructor_args.items()}
            res = seed_class.create(**python_args)
        else:
            res = seed_class.create()
        if not res:
            return Result.error("call_by_path: could not create seed instance", res)
        seed_instance = res.unwrapped
        obj["seed-instance"] = seed_instance
        method = getattr(seed_instance, method_name)
        if what in ["open", "configure", "close"] and params is not None:
            return method(path, params)
        elif what in ["register_opened_asset", "unregister_opened_asset"] and params is not None:
            # register_opened_asset(relative_path, asset, metadata)
            # path here is /opened/providers, but we need to pass the relative path from params
            return method(params.get("path"), params.get("asset"), params.get("metadata"))
        else:
            return method(path)

    # log(f"call_by_path: len path {len(path)}")
    if len(path) == 0:
        res = obj.get(attribute_name)
        if res is None:
            return Result.error(f"call_by_path: attribute '{attribute_name}' not found in path '{path}'")

        if what == "children-names":
            return Ok(list(res.keys()))
        else:
            return Ok(res)

    children = obj.get("children")
    if not children:
        return Result.error(f"call_by_path: attribute {attribute_name} not found in path '{path}'")

    child = children.get(path[0])
    if not child:
        return Result.error(f"call_by_path: child '{path[0]}' not found")

    return call_by_path(child, path[1:], what, params)

class PluginManager(TreeLike, Object):

    def __init__(self, label, plugins_path: Optional[str] = None):
        super().__init__()
        self._tree = None
        self._label = label
        self._plugins_path = plugins_path

    def get_children_names(self, path: DataPath) -> Result[None]:
        res = self._ensure_providers_loaded()
        if not res:
            return Result.error("PluginManager: error loading providers", res)
        return call_by_path(self._tree, path, "children-names")


    def get_metadata(self, path: DataPath) -> Dict[str, Any]:
        res = self._ensure_providers_loaded()
        if not res:
            return Result.error("PluginManager: error loading providers", res)
        res = call_by_path(self._tree, path, "metadata")
        if not res:
            return Result.error(f"PluginManager: could not retrieve metadata for path: {path}", res)
        return res

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
        res = self._ensure_providers_loaded()
        if not res:
            return Result.error("PluginManager: error loading providers", res)
        return call_by_path(self._tree, path, "open", *args, *kwargs)

    def configure(self, path: DataPath, params: Dict) -> Result[None]:
        """Delegate reconfig_asset to the appropriate provider manager"""
        res = self._ensure_providers_loaded()
        if not res:
            return Result.error("PluginManager: error loading providers", res)
        return call_by_path(self._tree, path, "configure", params)

    def close(self, path: DataPath) -> Result[None]:
        """Delegate close to the appropriate provider manager"""
        res = self._ensure_providers_loaded()
        if not res:
            return Result.error("PluginManager: error loading providers", res)
        return call_by_path(self._tree, path, "close", {})

    def _ensure_providers_loaded(self) -> Result[None]:
        """Lazy load all provider plugins."""
        # log("XXXXXXXXX ensure providers loaded")
        if self._tree:
            return Ok(None)
        tree = {
            "metadata": {
                "label": self._label
            },
            "children": {}
        }

        # Build list of provider directories from colon-separated path
        plugin_dirs = []
        if self._plugins_path:
            # Parse colon-separated paths
            for path_str in self._plugins_path.split(':'):
                path_str = path_str.strip()
                if path_str:
                    plugin_dirs.append(Path(path_str))
        else:
            # Default: plugins directory is alongside this file in src/imery/
            src_root = Path(__file__).parent
            plugin_dirs.append(src_root / "plugins")

        # Scan each provider directory
        for plugins_dir in plugin_dirs:
            if not plugins_dir.exists():
                continue

            # Scan each subdirectory in plugins_dir
            for plugin_dir in plugins_dir.iterdir():
                if not plugin_dir.is_dir():
                    continue

                main_py = plugin_dir / "main.py"
                if not main_py.exists():
                    continue

                plugin_name = plugin_dir.name

                try:
                    # Load the module dynamically
                    spec = importlib.util.spec_from_file_location(
                        f"imery.plugins.{plugin_name}.main",
                        main_py
                    )
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[spec.name] = module
                    spec.loader.exec_module(module)

                except Exception as e:
                    return Result.error(f"PluginManager: _ensure_providers_loaded: Could not load {main_py}", e)

        for device_manager in _pending_device_managers:
            instance = device_manager()

            # Call init() as per Object pattern
            res = instance.init()
            if not res:
                # Continue with other providers
                continue

            res = instance.get_metadata(DataPath("/"))
            if not res:
                return Result.error(f"could not retrieve metadata for '/', from {device_manager}")
            instance_metadata = res.unwrapped
            name = instance_metadata.get("name")
            if not name:
                return Result.error(f"'name' not found in metadata for '/', from {device_manager}")

            # Add provider directly to tree
            tree["children"][name] = {
                "seed-instance": instance
            }

        self._tree = tree
        return Ok(None)


    def init(self) -> Result[None]:
        return Ok(None)

    def dispose(self) -> Result[None]:
        return Ok(None)
    
    def as_tree(self, data_path: DataPath = None, depth: int = 0) -> Result[Union[dict]]:
        pass

