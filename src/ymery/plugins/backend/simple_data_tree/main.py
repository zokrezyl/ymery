# plugins/backend/simple_data_tree/main.py
"""
SimpleDataTree - Wrapper/Mapper around any Python data structure
Implements TreeLike interface for unified access to hierarchical data

Maps any Python data (primitives, dicts, lists, TreeLike) to TreeLike interface.
"Children aspect has priority" - if data can have children, it becomes a parent node.

EXAMPLES
========

Example 1: String primitive
----------------------------
Python: "hello world"

TreeLike behavior:
- get_children_names(/) → []
- get_metadata(/) → {"label": "hello world"}
- get(/label) → "hello world"


Example 2: Dict with primitives
--------------------------------
Python: {"name": "Alice", "age": 30}

TreeLike behavior:
- get_children_names(/) → ["name", "age"]
- get_metadata(/) → {"label": ""}
- get_metadata(/name) → {"label": "Alice"}
- get(/name/label) → "Alice"
- get_metadata(/age) → {"label": "30"}
- get(/age/label) → "30"

Note: Dict keys become child names. Values determine child metadata.
NO automatic conversion of key "name" to metadata field "label"!


Example 3: List
---------------
Python: ["apple", "banana", "cherry"]

TreeLike behavior:
- get_children_names(/) → ["0", "1", "2"]
- get_metadata(/) → {"label": ""}
- get_metadata(/0) → {"label": "apple"}
- get(/0/label) → "apple"


Example 4: Nested dict
-----------------------
Python: {"user": {"name": "Bob", "age": 25}, "status": "active"}

TreeLike behavior:
- get_children_names(/) → ["user", "status"]
- get_metadata(/) → {"label": ""}
- get_children_names(/user) → ["name", "age"]
- get_metadata(/user) → {"label": ""}
- get_metadata(/user/name) → {"label": "Bob"}
- get(/user/name/label) → "Bob"


Example 5: List of dicts
-------------------------
Python: [{"name": "Alice", "score": 95}, {"name": "Bob", "score": 87}]

TreeLike behavior:
- get_children_names(/) → ["0", "1"]
- get_metadata(/0) → {"label": ""}
- get_children_names(/0) → ["name", "score"]
- get_metadata(/0/name) → {"label": "Alice"}
- get(/0/name/label) → "Alice"


Example 6: Empty structures
----------------------------
Python: {} or []

TreeLike behavior:
- get_children_names(/) → []
- get_metadata(/) → {"label": ""}

Note: Empty containers are leaves (no children)


Example 7: TreeLike delegation
-------------------------------
Python: {"simple": "value", "nested_tree": DataTree(...)}

TreeLike behavior:
- get_children_names(/) → ["simple", "nested_tree"]
- get_metadata(/nested_tree) → Delegates to DataTree.get_metadata(/)
- get_children_names(/nested_tree) → Delegates to DataTree.get_children_names(/)

Note: TreeLike objects are transparent - all calls delegate through
"""

from typing import Union, List, Dict, Any
from ymery.result import Result, Ok
from ymery.backend.types import TreeLike
from ymery.types import DataPath
from ymery.types import Object
from ymery.decorators import tree_like


@tree_like
class SimpleDataTree(Object, TreeLike):
    """Maps any Python data structure to TreeLike interface"""

    name = "simple_data_tree"

    def __init__(self, dispatcher, plugin_manager=None, raw_arg=None):
        """
        Args:
            dispatcher: Event dispatcher (or data if called with single arg)
            plugin_manager: Plugin manager (optional)
            raw_arg: Any Python data - primitives, dict, list, or TreeLike
        """
        super().__init__()
        # Support both (data) and (dispatcher, plugin_manager, raw_arg) patterns
        if plugin_manager is None and raw_arg is None:
            self._data = dispatcher  # Called with just (data)
        else:
            self._data = raw_arg
        self._dispatcher = dispatcher if plugin_manager is not None else None
        self._plugin_manager = plugin_manager

    def init(self) -> Result[None]:
        return Ok(None)

    def dispose(self) -> Result[None]:
        return Ok(None)

    @property
    def as_tree(self, depth: int = -1):
        return self._data

    def _navigate(self, path: DataPath):
        """
        Navigate to a node in the data structure

        Args:
            path: DataPath to navigate

        Returns:
            Result with the data at path, or Error if not found
        """
        if len(path) == 0:
            return Ok(self._data)

        parts = path.as_list
        current = self._data

        for i, part in enumerate(parts):
            # If current is TreeLike, delegate remaining path
            if isinstance(current, TreeLike):
                remaining_parts = parts[i:]
                return Ok((current, DataPath(remaining_parts)))

            # Handle dict
            if isinstance(current, dict):
                if part not in current:
                    return Result.error(f"key '{part}' not found in dict at path '{path}'")
                current = current[part]

            # Handle list
            elif isinstance(current, list):
                try:
                    index = int(part)
                except ValueError:
                    return Result.error(f"'{part}' is not a valid index for list at path '{path}'")

                if index < 0 or index >= len(current):
                    return Result.error(f"index {index} out of range at path '{path}'")
                current = current[index]

            # Primitive - cannot navigate further
            else:
                return Result.error(f"cannot navigate through primitive value at '{part}' in path '{path}'")

        return Ok(current)

    def get_children_names(self, path: DataPath) -> Result[List[str]]:
        """
        Get children names at path

        Args:
            path: DataPath to the node

        Returns:
            Result with list of child names (dict keys or list indices)
        """
        res = self._navigate(path)
        if not res:
            return Result.error(f"get_children_names: navigation failed", res)

        node = res.unwrapped

        # Check if we hit a TreeLike (tuple result)
        if isinstance(node, tuple) and len(node) == 2:
            treelike, remaining_path = node
            return treelike.get_children_names(remaining_path)

        # Dict - return keys
        if isinstance(node, dict):
            return Ok(list(node.keys()))

        # List - return indices as strings
        if isinstance(node, list):
            return Ok([str(i) for i in range(len(node))])

        # Primitive or empty - no children
        return Ok([])

    def get_metadata(self, path: DataPath) -> Result[Dict]:
        """
        Get metadata for a node at path

        Args:
            path: DataPath to the node

        Returns:
            Result with metadata dict (always contains "label" key)
        """
        res = self._navigate(path)
        if not res:
            return Result.error(f"get_metadata: navigation failed", res)

        node = res.unwrapped

        # Check if we hit a TreeLike (tuple result)
        if isinstance(node, tuple) and len(node) == 2:
            treelike, remaining_path = node
            return treelike.get_metadata(remaining_path)

        # Get the key name (last component of path)
        key_name = path.filename() if len(path) > 0 else ""

        # Dict or list - label is the key name
        if isinstance(node, (dict, list)):
            return Ok({"label": key_name})

        # Primitive - label is "key: value"
        # Handles: str, int, float, bool, None
        if key_name:
            return Ok({"label": f"{key_name}: {str(node)}"})
        else:
            return Ok({"label": str(node)})

    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        """Get metadata keys using existing get_metadata"""
        res = self.get_metadata(path)
        if not res:
            return Result.error(f"SimpleDataTree: failed to get metadata for {path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            return Ok(list(metadata.keys()))
        return Result.error(f"SimpleDataTree: metadata is not a dict at {path}")

    def get(self, path: DataPath) -> Result[Any]:
        """
        Get metadata value - last component of path is the metadata key

        Args:
            path: DataPath where last component is metadata key (e.g., /user/name/label)

        Returns:
            Result with the metadata value
        """
        # Split path: node_path (all but last) and metadata_key (last)
        node_path = path.dirname()
        metadata_key = path.filename()

        # Navigate to node
        res = self._navigate(node_path)
        if not res:
            return Result.error(f"SimpleDataTree.get: navigation to {node_path} failed", res)

        node = res.unwrapped

        # Check if TreeLike
        if isinstance(node, tuple) and len(node) == 2:
            treelike, remaining_path = node
            # Reconstruct full path with key
            full_remaining = remaining_path / metadata_key
            return treelike.get(full_remaining)

        # Get metadata for this node
        metadata_res = self.get_metadata(node_path)
        if not metadata_res:
            return Result.error(f"SimpleDataTree.get: failed to get metadata at {node_path}", metadata_res)

        metadata = metadata_res.unwrapped

        if metadata_key not in metadata:
            return Result.error(f"SimpleDataTree.get: key '{metadata_key}' not found in metadata at {node_path}")

        return Ok(metadata[metadata_key])

    def set(self, path: DataPath, value: Any) -> Result[None]:
        """
        Set metadata value - NOT IMPLEMENTED (read-only for now)

        Args:
            path: DataPath where last component is metadata key
            value: Value to set

        Returns:
            Error - modification not supported yet
        """
        return Result.error("SimpleDataTree.set: modification not implemented (read-only)")

    def add_child(self, path: DataPath, name: str, data: Any) -> Result[None]:
        """
        Add child - NOT IMPLEMENTED (read-only)

        Args:
            path: DataPath to parent node
            name: Name of new child
            data: Data for new child

        Returns:
            Error - modification not supported
        """
        return Result.error("SimpleDataTree.add_child: modification not implemented (read-only)")
