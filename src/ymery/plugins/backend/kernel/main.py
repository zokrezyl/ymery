# plugins/backend/kernel/main.py
from typing import List, Dict, Any, Optional, Union

from ymery.backend.types import TreeLike, DeviceManager
from ymery.types import DataPath, Object, ActionHandler
from ymery.result import Result, Ok
from ymery.plugin_manager import call_by_path
from ymery.decorators import tree_like

from ymery.logging import log

from pprint import pp


class PathTransformer:
    pass


class ProvidersProxy:
    """Proxy that delegates to device-manager providers lazily."""

    def __init__(self, kernel):
        self._kernel = kernel

    def _get_provider_and_path(self, path: DataPath):
        """Get provider and remaining path from path like /waveform-st/..."""
        parts = path.as_list
        if len(parts) == 0:
            return None, None, path
        provider_name = parts[0]
        res = self._kernel._get_provider(provider_name)
        if not res:
            return None, res, path
        remaining = DataPath(parts[1:]) if len(parts) > 1 else DataPath("/")
        return res.unwrapped, None, remaining

    def get_children_names(self, path: DataPath) -> Result[List[str]]:
        if len(path) == 0 or str(path) == "/":
            res = self._kernel._plugin_manager.get_children_names(DataPath("/device-manager"))
            if not res:
                return Result.error("ProvidersProxy: failed to get device-manager list", res)
            return res
        provider, err, remaining = self._get_provider_and_path(path)
        if err:
            return err
        return provider.get_children_names(remaining)

    def get_metadata(self, path: DataPath) -> Result[Dict[str, Any]]:
        if len(path) == 0 or str(path) == "/":
            return Ok({"name": "providers", "label": "Providers"})
        provider, err, remaining = self._get_provider_and_path(path)
        if err:
            return err
        return provider.get_metadata(remaining)

    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        res = self.get_metadata(path)
        if not res:
            return Result.error(f"ProvidersProxy: failed to get metadata for {path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            return Ok(list(metadata.keys()))
        return Result.error(f"ProvidersProxy: metadata is not a dict at {path}")

    def get(self, path: DataPath) -> Result:
        provider, err, remaining = self._get_provider_and_path(path)
        if err:
            return err
        return provider.get(remaining)

    def open(self, path: DataPath, params: Dict) -> Result:
        provider, err, remaining = self._get_provider_and_path(path)
        if err:
            return Result.error(f"ProvidersProxy: could not open at path {path}", err)
        return provider.open(remaining, params)


class SettingsManager(Object, TreeLike):
    def dispose(self) -> Result[None]:
        return Ok(None)

    def init(self) -> Result[None]:
        return Ok(None)

    def get_children_names(self, path: DataPath) -> Result[List[str]]:
        return Ok([])

    def get_metadata(self, path: DataPath) -> Result[Dict]:
        return Ok({"name": "settings", "label": "settings", "type": "category"})

    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        """Get metadata keys using existing get_metadata"""
        res = self.get_metadata(path)
        if not res:
            return Result.error(f"SettingsManager: failed to get metadata for {path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            return Ok(list(metadata.keys()))
        return Result.error(f"SettingsManager: metadata is not a dict at {path}")

    def get(self, path: DataPath) -> Result:
        """Get metadata value - last component of path is the key"""
        node_path = path.dirname()
        key = path.filename()

        res = self.get_metadata(node_path)
        if not res:
            return Result.error(f"SettingsManager: failed to get metadata for {node_path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            if key in metadata:
                return Ok(metadata[key])
            return Result.error(f"SettingsManager: key '{key}' not found in metadata at {node_path}")
        return Result.error(f"SettingsManager: metadata is not a dict at {node_path}")

    def set(self, path: DataPath, value) -> Result[None]:
        """Set not implemented"""
        return Result.error("SettingsManager: set not implemented")

    def add_child(self, path: DataPath, value0) -> Result[None]:
        return Result.error("SettingsManager: add-child: not implemented")

    def as_tree(self, data_path: DataPath = None, depth: int = 0) -> Result[Union[dict]]:
        pass


class RegisteredObjectsManager(Object, TreeLike):
    def dispose(self) -> Result[None]:
        return Ok(None)

    def init(self) -> Result[None]:
        return Ok(None)

    def get_children_names(self, path: DataPath) -> Result[List[str]]:
        return Ok([])

    def get_metadata(self, path: DataPath) -> Result[Dict]:
        return Ok({"name": "windows", "label": "windows", "type": "category"})

    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        """Get metadata keys using existing get_metadata"""
        res = self.get_metadata(path)
        if not res:
            return Result.error(f"RegisteredObjectsManager: failed to get metadata for {path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            return Ok(list(metadata.keys()))
        return Result.error(f"RegisteredObjectsManager: metadata is not a dict at {path}")

    def get(self, path: DataPath) -> Result:
        """Get metadata value - last component of path is the key"""
        node_path = path.dirname()
        key = path.filename()

        res = self.get_metadata(node_path)
        if not res:
            return Result.error(f"RegisteredObjectsManager: failed to get metadata for {node_path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            if key in metadata:
                return Ok(metadata[key])
            return Result.error(f"RegisteredObjectsManager: key '{key}' not found in metadata at {node_path}")
        return Result.error(f"RegisteredObjectsManager: metadata is not a dict at {node_path}")

    def set(self, path: DataPath, value) -> Result[None]:
        """Set not implemented"""
        return Result.error("RegisteredObjectsManager: set not implemented")

    def add_child(self, path: DataPath, value0) -> Result[None]:
        return Result.error("RegisteredObjectsManager: add-child: not implemented")

    def as_tree(self, data_path: DataPath = None, depth: int = 0) -> Result[Union[dict]]:
        pass


@tree_like
class Kernel(DeviceManager, ActionHandler):
    """
    Backend that manages all assets: plugins, opened plugins, settings, and windows.

    Asset tree structure:
    /
    ├─ /available (all available assets)
    ├──── /available/plugins (plugin plugins)
    │   ├──── /available/plugins/alsa
    │   └──── /avaialble/plugins/Soundfile
    ├── /available/settings (configuration)
    """

    name = "kernel"

    def __init__(self, dispatcher, plugin_manager, raw_arg=None):
        super().__init__()
        self._dispatcher = dispatcher
        self._plugin_manager = plugin_manager
        self._raw_arg = raw_arg

        self._providers = {}

        self._tree = {
            "metadata": {
                "name": "kernel",
                "label": "Kernel"
            },
            "children": {
                "providers": {
                    "seed-instance": ProvidersProxy(self)
                },
                "settings": {
                    "seed-class": SettingsManager,
                    "seed-instance": None,
                    "constructor-args": {
                    }
                },
                "windows": {
                    "seed-class": RegisteredObjectsManager,
                    "seed-instance": None
                }
            }
        }

    # ========== AssetProvider Interface ==========
    def get_children_names(self, path: DataPath) -> Result[List[str]]:
        """Get children names for a given path in the asset tree."""
        res = call_by_path(self._tree, path, "children-names")
        if not res:
            return Result.error(f"Kernel: could not retrieve children names for path {path}", res)
        return res

    def get_metadata(self, path: DataPath) -> Result[Dict[str, Any]]:
        res = call_by_path(self._tree, path, "metadata")
        if not res:
            return Result.error(f"Kernel: could not retrieve metadata for path: {path}", res)
        return res

    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        """Get metadata keys using existing get_metadata"""
        res = self.get_metadata(path)
        if not res:
            return Result.error(f"Kernel: failed to get metadata for {path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            return Ok(list(metadata.keys()))
        return Result.error(f"Kernel: metadata is not a dict at {path}")

    def get(self, path: DataPath) -> Result:
        """Get metadata value - last component of path is the key"""
        node_path = path.dirname()
        key = path.filename()

        res = self.get_metadata(node_path)
        if not res:
            return Result.error(f"Kernel: failed to get metadata for {node_path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            if key in metadata:
                return Ok(metadata[key])
            return Result.error(f"Kernel: key '{key}' not found in metadata at {node_path}")
        return Result.error(f"Kernel: metadata is not a dict at {node_path}")

    def set(self, path: DataPath, value) -> Result[None]:
        """Set metadata value at path - supports root level metadata like /selection"""
        # For root-level metadata (e.g., /selection)
        if len(path) == 1:
            key = path.filename()
            self._tree["metadata"][key] = value
            return Ok(None)

        # For now, only root-level metadata is supported
        return Result.error(f"Kernel: set: only root-level metadata supported, got path '{path}'")

    def add_child(self, path: DataPath, value) -> Result[None]:
        """Set not implemented"""
        return Result.error("Kernel: add_child: not implemented")

    def open(self, path: DataPath, params: Dict) -> Result:
        """Create/open an asset at the given path."""
        res = call_by_path(self._tree, path, "open", params)

        # Post event to dispatcher
        if res:
            # Success - convert result to string
            data = str(res.unwrapped)
        else:
            # Error - use as_tree property
            data = res.as_tree

        event = {
            "name": "open",
            "source": "kernel",
            "path": str(path),
            "data": data
        }
        self._dispatcher.dispatch_event(event)

        if not res:
            return Result.error(f"Kernel: could not open asset at path {path}", res)

        return res

    def configure(self, path: DataPath, params: Dict) -> Result[None]:
        """configure parameters of an existing asset."""
        res = call_by_path(self._tree, path, "reconfig_asset", params)
        if not res:
            return Result.error(f"Kernel: could not configure asset at path {path}", res)
        return res

    def close(self, path: DataPath) -> Result[None]:
        """close an asset at the given path."""
        res = call_by_path(self._tree, path, "delete_asset", {})
        if not res:
            return Result.error(f"Kernel: could not close asset at path {path}", res)
        return res

    # ========== ActionHandler Interface ==========

    def handle_action(self, action: dict):
        """Handle actions from dispatcher."""
        action_type = action.get("action")

        if action_type == "open-asset":
            data = action.get("data", {})
            plugin_class = data.get("plugin-class")
            constructor_args = data.get("constructor-args", {})
            path = data.get("path")

            # TODO: Implement open-asset action

    def register_object(self, path: Union[str, DataPath], object) -> Result[None]:
        """
        registers an object for 'consumption'
        this is mainly used by ui to register for instance layers that can be linked to other layers
        """
        pass

    def _get_provider(self, provider_name: str) -> Result:
        """Lazily get or create a provider instance."""
        if provider_name in self._providers:
            return Ok(self._providers[provider_name])

        res = self._plugin_manager.get_metadata(DataPath(f"/device-manager/{provider_name}"))
        if not res:
            return Result.error(f"Kernel: failed to get metadata for device-manager '{provider_name}'", res)

        provider_class = res.unwrapped.get("class")
        if not provider_class:
            return Result.error(f"Kernel: no class found for device-manager '{provider_name}'")

        res = provider_class.create(self._dispatcher, self._plugin_manager)
        if not res:
            return Result.error(f"Kernel: failed to create device-manager '{provider_name}'", res)

        self._providers[provider_name] = res.unwrapped
        return Ok(res.unwrapped)

    def init(self) -> Result[None]:
        return Ok(None)

    def dispose(self) -> Result[None]:
        #TODO dispose all plugins, opened assets etc
        return Ok(None)

    def as_tree(self, data_path: Optional[DataPath] = None, depth: int = 0) -> Result[None]:
        pass
