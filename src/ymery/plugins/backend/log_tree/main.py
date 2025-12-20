# plugins/backend/log_tree/main.py
"""
LogTree - TreeLike wrapper around the RingBuffer logging handler

Root level returns log entry indices as children.
Deeper levels delegate to SimpleDataTree instances wrapping each entry's error dict.
"""

from typing import List, Dict, Any, Optional

from ymery.backend.types import TreeLike
from ymery.types import DataPath, Object
from ymery.result import Result, Ok
from ymery.decorators import tree_like
from ymery.logging import get_ring_buffer, LogEntry


@tree_like
class LogTree(Object, TreeLike):
    """
    TreeLike wrapper around RingBufferHandler for log display.

    - get_children_names("/") returns ["0", "1", "2", ...]
    - get_children_names("/0/...") delegates to SimpleDataTree for entry 0
    """

    name = "log-tree"

    def __init__(self, dispatcher, plugin_manager, raw_arg=None):
        super().__init__()
        self._dispatcher = dispatcher
        self._plugin_manager = plugin_manager
        self._entry_trees: Dict[int, Any] = {}  # Cache of SimpleDataTree instances

    def init(self) -> Result[None]:
        return Ok(None)

    def dispose(self) -> Result[None]:
        return Ok(None)

    def _get_entries(self) -> List[LogEntry]:
        """Get current log entries from ring buffer."""
        buffer = get_ring_buffer()
        if buffer is None:
            return []
        return buffer.get_entries()

    def _get_entry_tree(self, index: int) -> Result[Any]:
        """Get or create SimpleDataTree wrapper for a log entry."""
        if index in self._entry_trees:
            return Ok(self._entry_trees[index])

        entries = self._get_entries()
        if index < 0 or index >= len(entries):
            return Result.error(f"LogTree: index {index} out of range")

        entry = entries[index]
        msg = entry.msg

        # Get the tree dict from the message
        if hasattr(msg, 'as_tree'):
            tree_dict = msg.as_tree
        elif isinstance(msg, dict):
            tree_dict = msg
        else:
            # Plain message - wrap in a simple dict
            tree_dict = {"message": str(msg)}

        # Get SimpleDataTree class from plugin_manager
        res = self._plugin_manager.get_metadata(DataPath("/tree-like/simple-data-tree"))
        if not res:
            return Result.error("LogTree: failed to get SimpleDataTree class", res)

        SimpleDataTree = res.unwrapped.get("class")
        if not SimpleDataTree:
            return Result.error("LogTree: SimpleDataTree class not found")

        # Create SimpleDataTree instance
        res = SimpleDataTree.create(tree_dict)
        if not res:
            return Result.error("LogTree: failed to create SimpleDataTree", res)

        self._entry_trees[index] = res.unwrapped
        return Ok(res.unwrapped)

    def get_children_names(self, path: DataPath) -> Result[List[str]]:
        """Get children names at path."""
        if path == "/" or len(path) == 0:
            # Root - return indices of log entries
            entries = self._get_entries()
            return Ok([str(i) for i in range(len(entries))])

        # Delegate to SimpleDataTree for this entry
        try:
            index = int(path[0])
        except ValueError:
            return Result.error(f"LogTree: invalid index '{path[0]}'")

        res = self._get_entry_tree(index)
        if not res:
            return Result.error("LogTree: failed to get entry tree", res)

        entry_tree = res.unwrapped
        remaining_path = DataPath(path.as_list[1:]) if len(path) > 1 else DataPath("/")
        return entry_tree.get_children_names(remaining_path)

    def get_metadata(self, path: DataPath) -> Result[Dict[str, Any]]:
        """Get metadata for a node at path."""
        entries = self._get_entries()

        if path == "/" or len(path) == 0:
            # Root metadata
            return Ok({
                "name": "log",
                "label": "Log",
                "type": "log-tree",
                "entry-count": len(entries)
            })

        # Delegate to SimpleDataTree for this entry
        try:
            index = int(path[0])
        except ValueError:
            return Result.error(f"LogTree: invalid index '{path[0]}'")

        res = self._get_entry_tree(index)
        if not res:
            return Result.error("LogTree: failed to get entry tree", res)

        entry_tree = res.unwrapped
        remaining_path = DataPath(path.as_list[1:]) if len(path) > 1 else DataPath("/")

        # Get metadata from the entry tree
        res = entry_tree.get_metadata(remaining_path)
        if not res:
            return res

        metadata = res.unwrapped

        # For root of entry (remaining_path is empty), add entry-level info
        if len(path) == 1:
            entry = entries[index]
            metadata["uid"] = entry.uid
            metadata["level"] = entry.level
            metadata["level-name"] = entry.level_name
            metadata["time"] = entry.timestamp
            # Override label with entry info
            msg_str = str(entry.msg)[:60]
            metadata["label"] = f"[{entry.level_name}] {msg_str}"

        return Ok(metadata)

    def get_metadata_keys(self, path: DataPath) -> Result[List[str]]:
        """Get metadata keys at path."""
        res = self.get_metadata(path)
        if not res:
            return Result.error("LogTree: failed to get metadata", res)
        return Ok(list(res.unwrapped.keys()))

    def get(self, path: DataPath) -> Result[Any]:
        """Get metadata value."""
        if len(path) == 0:
            return Result.error("LogTree: path cannot be empty")

        # Delegate to SimpleDataTree
        try:
            index = int(path[0])
        except ValueError:
            return Result.error(f"LogTree: invalid index '{path[0]}'")

        res = self._get_entry_tree(index)
        if not res:
            return res

        entry_tree = res.unwrapped
        remaining_path = DataPath(path.as_list[1:]) if len(path) > 1 else DataPath("/")
        return entry_tree.get(remaining_path)

    def set(self, path: DataPath, value: Any) -> Result[None]:
        return Result.error("LogTree: read-only")

    def add_child(self, path: DataPath, name: str, data: Any) -> Result[None]:
        return Result.error("LogTree: read-only")

    def clear(self) -> Result[None]:
        """Clear the log buffer."""
        buffer = get_ring_buffer()
        if buffer is None:
            return Result.error("LogTree: ring buffer not initialized")
        buffer.clear()
        self._entry_trees.clear()
        return Ok(None)

    @property
    def as_tree(self) -> Dict:
        """Required by TreeLike interface."""
        return {"metadata": {"label": "Log"}}
