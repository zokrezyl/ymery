# plugins/backend/data_tree/main.py
"""
DataTree - Wrapper around dict with explicit children/metadata structure
Implements TreeLike interface for unified access to hierarchical data

Expected data format:
{
    "children": {
        "child1": {"children": {...}, "metadata": {...}},
        "child2": {"metadata": {...}}
    },
    "metadata": {"key1": "value1", ...}
}
"""

from typing import Union, List, Dict
from ymery.result import Result, Ok
from ymery.backend.types import TreeLike
from ymery.types import DataPath, Object
from ymery.decorators import tree_like


@tree_like
class DataTree(Object, TreeLike):
    """Wrapper around dict with explicit children/metadata structure"""

    name = "data-tree"

    def __init__(self, dispatcher, plugin_manager, raw_arg=None):
        super().__init__()
        self._dispatcher = dispatcher
        self._plugin_manager = plugin_manager
        self._data = raw_arg

    def init(self) -> Result[None]:
        if self._data is None:
            return Result.error("DataTree: raw_arg is required")
        if not isinstance(self._data, dict):
            return Result.error(f"DataTree: raw_arg must be dict, got {type(self._data).__name__}")
        return Ok(None)

    def dispose(self) -> Result[None]:
        return Ok(None)

    @property
    def as_tree(self):
        return self._data

    def _navigate(self, path: DataPath):
        """
        Navigate to a node in the data structure

        Args:
            path: DataPath to navigate

        Returns:
            Result with the node dict at path, or Error if not found
        """
        if len(path) == 0:
            return Ok(self._data)

        parts = path.as_list
        current = self._data

        for i, part in enumerate(parts):
            # Check if current node is a dict
            if not isinstance(current, dict):
                current_path = DataPath(parts[:i])
                return Result.error(f"node at path '{current_path}' is not a dict (got {type(current).__name__}), cannot navigate to '{part}'")

            # Get children dict
            children = current.get("children")
            if not children:
                return Result.error(f"node at path has no children, cannot navigate to '{part}'")

            if not isinstance(children, dict):
                return Result.error(f"children must be dict, got {type(children)}")

            # Get child by key
            if part not in children:
                return Result.error(f"child '{part}' not found in path '{path}'")

            current = children[part]

            # Check if current is a TreeLike instance
            if isinstance(current, TreeLike):
                # Return tuple to signal delegation needed
                remaining_parts = parts[i+1:]
                return Ok((current, DataPath(remaining_parts)))

        return Ok(current)

    def get(self, path: DataPath) -> Result[Union[str, int, float, bool, dict, list]]:
        """
        Get value at path

        Args:
            path: DataPath to navigate

        Returns:
            Result with the value at path, or Error if not found
        """
        res = self._navigate(path)
        if not res:
            return res

        value = res.unwrapped

        # Check if we hit a TreeLike (tuple result)
        if isinstance(value, tuple) and len(value) == 2:
            treelike, remaining_path = value
            # For get(), we return the metadata value
            res = treelike.get_metadata(remaining_path)
            if not res:
                return Result.error("get: TreeLike.get_metadata failed", res)
            return Ok(res.unwrapped.get("value"))

        return Ok(value)

    def open(self, path: DataPath, *args, **kwargs) -> Result[Union[str, int, float, bool, dict, list]]:
        """
        Get value at path

        Args:
            path: DataPath to navigate

        Returns:
            Result with the value at path, or Error if not found
        """
        res = self._navigate(path)
        if not res:
            return res

        value = res.unwrapped

        # Check if we hit a TreeLike (tuple result)
        if isinstance(value, tuple) and len(value) == 2:
            treelike, remaining_path = value
            # For get(), we return the metadata value
            if not hasattr(treelike, "open"):
                return Result.error(f"DataTree: open: TreeLike '{type(treelike)}' does not have method 'open'")
            res = treelike.open(remaining_path, *args, **kwargs)
            if not res:
                return Result.error("get: TreeLike.open failed", res)
            return Ok(res.unwrapped)

        return Ok(value)

    def set(self, path: DataPath, value) -> Result[None]:
        """
        Set value at path

        Args:
            path: DataPath to the value
            value: Value to set

        Returns:
            Ok(None) or Error if path doesn't exist
        """
        if len(path) == 0:
            return Result.error("path cannot be empty")

        parts = path.as_list
        current = self._data

        # Navigate to parent
        for part in parts[:-1]:
            if isinstance(current, dict):
                if part not in current:
                    return Result.error(f"key '{part}' not found in path '{path}'")
                current = current[part]
            elif isinstance(current, list):
                try:
                    index = int(part)
                except ValueError:
                    return Result.error(f"'{part}' is not a valid index for list in path '{path}'")

                if index < 0 or index >= len(current):
                    return Result.error(f"index {index} out of range in path '{path}'")
                current = current[index]
            else:
                return Result.error(f"cannot navigate through primitive value at '{part}' in path '{path}'")

        # Set the final value
        final_part = parts[-1]
        if isinstance(current, dict):
            if final_part not in current:
                return Result.error(f"key '{final_part}' not found in path '{path}'")
            current[final_part] = value
        elif isinstance(current, list):
            try:
                index = int(final_part)
            except ValueError:
                return Result.error(f"'{final_part}' is not a valid index for list in path '{path}'")

            if index < 0 or index >= len(current):
                return Result.error(f"index {index} out of range in path '{path}'")
            current[index] = value
        else:
            return Result.error(f"cannot set value on primitive at '{final_part}' in path '{path}'")

        return Ok(None)

    def add_child(self, path: DataPath, name: str, data: any) -> Result[None]:
        """
        Add a new child to the node at path

        Args:
            path: DataPath to the parent node
            name: Name of the new child
            data: Data for the new child (dict with metadata/children, or any value)

        Returns:
            Ok(None) or Error if parent doesn't exist or child already exists
        """
        # Navigate to parent node
        res = self._navigate(path)
        if not res:
            return Result.error(f"add_child: navigation to parent '{path}' failed", res)

        parent = res.unwrapped

        # Check if TreeLike delegation
        if isinstance(parent, tuple) and len(parent) == 2:
            treelike, remaining_path = parent
            return treelike.add_child(remaining_path, name, data)

        # Ensure parent is a dict
        if not isinstance(parent, dict):
            return Result.error(f"add_child: parent at '{path}' must be dict, got {type(parent)}")

        # Ensure parent has children dict
        if "children" not in parent:
            parent["children"] = {}

        children = parent["children"]
        if not isinstance(children, dict):
            return Result.error(f"add_child: children at '{path}' must be dict, got {type(children)}")

        # Check if child already exists
        if name in children:
            return Result.error(f"add_child: child '{name}' already exists at '{path}'")

        # Wrap data in DataTree format if it's just metadata
        if isinstance(data, dict) and ("metadata" in data or "children" in data):
            # Already in DataTree format
            children[name] = data
        else:
            # Wrap as metadata
            children[name] = {"metadata": data}

        return Ok(None)

    def get_children_names(self, path: DataPath) -> Result[List[str]]:
        """
        Get children names at path (TreeLike interface)

        Args:
            path: DataPath to the node

        Returns:
            Result with list of child names
        """
        res = self._navigate(path)
        if not res:
            return Result.error(f"get_children_names: navigation failed", res)

        node = res.unwrapped

        # Check if we hit a TreeLike (tuple result)
        if isinstance(node, tuple) and len(node) == 2:
            treelike, remaining_path = node
            return treelike.get_children_names(remaining_path)

        # Node must be dict
        if not isinstance(node, dict):
            return Result.error(f"DataTree.get_children_names: node is not a dict")

        # If no children key, return empty list (leaf node)
        if "children" not in node:
            return Ok([])

        children = node["children"]
        if not isinstance(children, dict):
            return Result.error(f"DataTree.get_children_names: 'children' must be dict, got {type(children)}")

        return Ok(list(children.keys()))

    def get_metadata(self, path: DataPath) -> Result[Dict]:
        """
        Get metadata for a node at path (TreeLike interface)

        Args:
            path: DataPath to the node

        Returns:
            Result with metadata dict
        """
        res = self._navigate(path)
        if not res:
            return Result.error(f"get_metadata: navigation failed", res)

        node = res.unwrapped

        # Check if we hit a TreeLike (tuple result)
        if isinstance(node, tuple) and len(node) == 2:
            treelike, remaining_path = node
            return treelike.get_metadata(remaining_path)

        # Node must be dict
        if not isinstance(node, dict):
            return Result.error(f"DataTree.get_metadata: node is not a dict")

        # Return metadata if present, otherwise empty dict
        metadata = node.get("metadata", {})
        if not isinstance(metadata, dict):
            return Result.error(f"DataTree.get_metadata: 'metadata' must be dict, got {type(metadata)}")

        return Ok(metadata)

    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        """Get metadata keys using existing get_metadata"""
        res = self.get_metadata(path)
        if not res:
            return Result.error(f"DataTree: failed to get metadata for {path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            return Ok(list(metadata.keys()))
        return Result.error(f"DataTree: metadata is not a dict at {path}")

    def get(self, path: DataPath) -> Result:
        """Get metadata value - last component of path is the key"""
        # Split path: node_path (all but last) and metadata_key (last)
        node_path = path.dirname()
        metadata_key = path.filename()

        # Navigate to node
        res = self._navigate(node_path)
        if not res:
            return Result.error(f"DataTree.get: navigation to {node_path} failed", res)

        node = res.unwrapped

        # Check if TreeLike
        if isinstance(node, tuple) and len(node) == 2:
            treelike, remaining_path = node
            # Reconstruct full path with key
            full_remaining = remaining_path / metadata_key
            return treelike.get(full_remaining)

        # Node must be dict
        if not isinstance(node, dict):
            return Result.error(f"DataTree.get: node not dict")

        metadata = node.get("metadata")
        if not isinstance(metadata, dict):
            return Result.error(f"DataTree.get: no metadata")

        if metadata_key not in metadata:
            return Result.error(f"DataTree.get: key '{metadata_key}' not found")

        return Ok(metadata[metadata_key])

    def set(self, path: DataPath, value) -> Result[None]:
        """Set metadata value - last component of path is the key"""
        # Split path: node_path (all but last) and metadata_key (last)
        node_path = path.dirname()
        metadata_key = path.filename()

        # Navigate to node
        res = self._navigate(node_path)
        if not res:
            return Result.error(f"DataTree.set: navigation to {node_path} failed", res)

        node = res.unwrapped

        # Check if TreeLike
        if isinstance(node, tuple) and len(node) == 2:
            treelike, remaining_path = node
            # Reconstruct full path with key
            full_remaining = remaining_path / metadata_key
            return treelike.set(full_remaining, value)

        # Node must be dict
        if not isinstance(node, dict):
            return Result.error(f"DataTree.set: node not dict")

        # Ensure metadata exists
        if "metadata" not in node:
            node["metadata"] = {}

        metadata = node["metadata"]
        if not isinstance(metadata, dict):
            return Result.error(f"DataTree.set: metadata not dict")

        # Set key in metadata
        metadata[metadata_key] = value
        return Ok(None)
