from typing import List, Dict, Any, Optional, Union

from imery.backend.types import TreeLike, DeviceManager
from imery.types import DataPath, Object, ActionHandler
from imery.result import Result, Ok
from imery.plugin_manager import call_by_path

from imery.logging import log

from pprint import pp

# objects in WaeW app are organised in a VFS like structure. Objects are called assets, not files as 
# for some users naming file an abstraction that is not really a file may be confusing
# Thus instead of VFS we will use VAS, virtual asset structure
# The kernel is the interface to access those objects/assets
# the rooot contains two main entries
# -> available assets
# -> maounted assets
# available assets are those assets that can be mounted thus used in the application
# the available assets are grouped into their providers
# -> alsa
# -> filesystem
# -> jack
# -> LDSPA
#
# each provider may provide further structures, for instance LDSPA may have entries per plugin




class PathTransformer:
    pass

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



class Kernel(DeviceManager, ActionHandler):
    """
    Backend that manages all assets: plugins, opened providers, settings, and windows.

    Asset tree structure:
    /
    ├─ /available (all available assets)
    ├──── /available/providers (provider plugins)
    │   ├──── /available/providers/alsa
    │   └──── /avaialble/providers/Soundfile
    ├── /available/settings (configuration)
    """


    def __init__(self, dispatcher, plugin_manager):
        super().__init__()
        self._dispatcher = dispatcher

        self._tree = {
            "metadata": {
                "name": "kernel",
                "label": "Kernel"
            },
            "children": {
                "providers": {
                    "seed-instance": plugin_manager
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
        """Get children names for a given path in the asset tree.

        Returns list of child names (not full paths).
        Names are used to compose the next level path.
        """
        res = call_by_path(self._tree, path, "children-names")
        if not res:
            return Result.error(f"Kernel: could not retrieve children names for path {path}", res)

        return res


    def get_metadata(self, path: DataPath) -> Dict[str, Any]:
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
        # Create asset - PluginManager handles both /available and /opened branches
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
            provider_class = data.get("provider-class")
            constructor_args = data.get("constructor-args", {})
            path = data.get("path")

            # TODO: Implement open-asset action

    def register_object(self, path: Union[str, DataPath], object) -> Result[None]:
        """
        registers an object for 'consumption'
        this is mainly used by ui to register for instance layers that can be linked to other layers
        """
        pass

    def init(self) -> Result[None]:
        return Ok(None)

    def dispose(self) -> Result[None]:
        #TODO dispose all providers, opened assets etc
        return Ok(None)
    
    def as_tree(self, data_path: Optional[DataPath] = None, depth: int = 0) -> Result[None]:
        pass


def test():
    from pprint import pprint
    res = Kernel.create()

    if not res:
        print("could not create backend", res) 
    backend = res.unwrapped

    alsa_root = DataPath("/available/providers/alsa/cards/10/0/0")

    res = backend.get_children_names(alsa_root)
    if not res:
        print("error retrieving children names", res)

    children = res.unwrapped

    print(children)

    res = backend.get_metadata(alsa_root)
    if not res:
        print("error retrieving metadata", res)

    children = res.unwrapped

    return

    children = res.unwrapped
    for child in children:
        print(f"{child}:")
        child_root = alsa_root / child
        res = backend.get_children_names(child_root)
        if not res:
            print("error")
        child_children = res.unwrapped
        for child_child in child_children:
            print(f"  {child_child}:")



    print("done")
    return
    if False:
        metadata = backend.get_metadata(DataPath("/available/providers/filesystem/tmp"))
        if not metadata:
            print("error retrieving ")

    res = backend.get_children_names(DataPath("/available/providers/filesystem/mounts"))
    if not res:
        print("error retrieving children names")

    names = res.unwrapped
    print(names)


    # metadata = backend.get_metadata("/available/providers/filesystem/mounts/tmp")
    # print(metadata)

    return

    if False:
        # Get root
        print("\n\n\nRoot:")
        print("  Children:", backend.get_children_names("/").unwrapped)
        print("  Metadata:", backend.get_metadata("/"))
        print()

        # Get providers
        #print("nonexistent:", backend.get_children_names("/nonexistent").as_tree)
        print("\navailable:", backend.get_children_names("/available").unwrapped)
    print("\n")
    print("\n")
    print("\n")
    print("\n/available/providers:\n")
    print(backend.get_children_names("/available/providers").unwrapped)


    pcms_root = DataPath("/available/providers/alsa/pcms")
    res = backend.get_children_names(pcms_root)
    if not res:
        print(f"could not retrieve pcms")
    pcms = res.unwrapped
    print("pcms:")
    pp(pcms)

    for pcm in pcms:
        pcm_path = pcms_root / pcm
        print(f"pcm_root: {pcms_root}, pcm_path: {pcm_path}")
        res = backend.get_metadata(pcms_root / pcm)
        if not res:
            # print("error", res)
            continue
        pcm = res.unwrapped

    jack_readable_clients_root = DataPath("/available/providers/jack/readable-clients")
    res = backend.get_children_names(jack_readable_clients_root)
    if not res:
        print(f"could not retrieve jacks")
        return
    jack_readable_clients = res.unwrapped
    print("pcms:")
    pp(jack_readable_clients)

    for jack in jack_readable_clients:
        jack_path = jack_readable_clients_root / jack
        print(f"YYYYY jack_root: {jack_readable_clients_root}, pcm_path: {jack_path}")
        res = backend.get_metadata(jack_path)
        if not res:
            print("error", res)
            continue
        jack = res.unwrapped

    #print(backend.get_children_names("/available/providers/jack/readable-clients").unwrapped)
    return
    print(backend.get_children_names("/available/providers/alsa").unwrapped)
    print("/available/providers/settings:", backend.get_children_names("/available/providers/settings").unwrapped)
    print("  Children:", plugins)
    print()

    # Test each plugin
    for plugin_path in plugins[:2]:  # First 2 plugins
        print(f"Testing: {plugin_path}")
        metadata = backend.get_metadata(plugin_path)
        pprint(metadata)

        children = backend.get_children(plugin_path)
        print(f"  Children ({len(children)}): {children[:3]}...")  # First 3
        print()


if __name__ == "__main__":
    test()
