import re
from imery.types import DataPath, Object, EventHandler, TreeLike
from imery.result import Result, Ok
from imery.backend.data_tree import DataTree
from typing import Optional, Dict, Any, Union, List

# Pattern for @ references: @path or $tree@path
# Reference chars: alphanumeric, hyphen, underscore, slash, dot (for ..)
REF_PATTERN = re.compile(r'(\$[a-zA-Z_-]+)?@([a-zA-Z0-9_/.-]+)')


class DataBag(Object):
    """
    Helper class that implements the logic of handling (read/write) of field values of a widget
    The value can be static in the definition of the widget or obtained from the tree like data

    Supports template references:
    - @path - path in main data tree (relative to current)
    - @/abs/path - absolute path in main tree
    - @../parent - parent-relative path
    - $tree@path - path in named tree
    - $tree@/abs - absolute path in named tree
    """
    def __init__(self, data_trees: Dict, main_data_key: str, main_data_path: DataPath, static: Optional[Dict]):
        self._data_trees = data_trees if data_trees else {}
        self._main_data_key = main_data_key
        self._main_data_path = main_data_path
        self._static = static

    @property
    def as_tree(self):
        tree = self._data_trees.get(self._main_data_key)
        return {
            "data-path": str(self._main_data_path),
            "static": self._static,
            "main-data-tree": tree.as_tree if tree else None,
        }

    def init(self) -> Result[None]:
        # Validate static type
        if self._static is not None and not isinstance(self._static, (str, dict)):
            return Result.error(f"DataBag.init: static must be None, str, or dict, got {type(self._static)}")

        # Extract 'data' from static - becomes the main data tree
        # Each top-level key becomes a tree ID, first one becomes main tree
        if self._static and isinstance(self._static, dict) and "data" in self._static:
            widget_data = self._static["data"]
            if isinstance(widget_data, dict):
                first_tree_id = None
                for tree_id, tree_content in widget_data.items():
                    # Check for key conflict
                    if tree_id in self._data_trees:
                        return Result.error(f"DataBag.init: data key '{tree_id}' already exists")

                    tree = DataTree(tree_content)
                    res = tree.init()
                    if not res:
                        return Result.error(f"DataBag.init: failed to init DataTree '{tree_id}'", res)

                    self._data_trees[tree_id] = tree
                    if first_tree_id is None:
                        first_tree_id = tree_id

                # First tree becomes the main tree
                if first_tree_id:
                    self._main_data_key = first_tree_id
                    self._main_data_path = DataPath("/")

        return Ok(None)

    def dispose(self) -> Result[None]:
        return Ok(None)

    def get_data_path(self) -> Result[DataPath]:
        """Get the current data path"""
        if self._main_data_path is None:
            return Result.error("DataBag.get_data_path: no data path available")
        return Ok(self._main_data_path)

    def get_data_path_str(self) -> Result[str]:
        """Get the current data path as string"""
        if self._main_data_path is None:
            return Result.error("DataBag.get_data_path_str: no data path available")
        return Ok(str(self._main_data_path))

    def _is_reference(self, value: Any) -> bool:
        """Check if value is a template reference string"""
        if not isinstance(value, str):
            return False
        return '@' in value

    def _resolve_reference(self, ref_str: str) -> Result[Any]:
        """
        Resolve a reference string like @path or $tree@path

        Returns the value at the referenced path.
        """
        # Find all references in the string
        matches = list(REF_PATTERN.finditer(ref_str))

        if not matches:
            # No references found, return as-is
            return Ok(ref_str)

        # Check if the entire string is a single reference (no interpolation needed)
        if len(matches) == 1 and matches[0].group(0) == ref_str:
            # Single reference - return the actual value (preserves type)
            return self._resolve_single_ref(matches[0])

        # Multiple references or mixed content - string interpolation
        result = ref_str
        for match in reversed(matches):  # Reverse to preserve positions
            res = self._resolve_single_ref(match)
            if not res:
                # Replace with error placeholder
                replacement = f"<{match.group(0)}?>"
            else:
                replacement = str(res.unwrapped)
            result = result[:match.start()] + replacement + result[match.end():]

        return Ok(result)

    def _resolve_single_ref(self, match: re.Match) -> Result[Any]:
        """Resolve a single reference match"""
        tree_name = match.group(1)  # $tree or None
        path_str = match.group(2)   # the path after @

        # Determine which tree to use
        if tree_name:
            # Named tree: $tree@path
            tree_key = tree_name[1:]  # Remove $ prefix
            tree = self._data_trees.get(tree_key) if self._data_trees else None
            if not tree:
                return Result.error(f"DataBag: unknown tree '{tree_key}'")
            # Named trees (like $local) always use root-relative paths
            # So $local@label is equivalent to $local@/label
            if not path_str.startswith('/'):
                path_str = '/' + path_str
        else:
            # Main tree: @path
            tree = self._data_trees.get(self._main_data_key)
            if not tree:
                return Result.error(f"DataBag: no main tree available for reference '@{path_str}'")

        # Resolve path
        if path_str.startswith('/'):
            # Absolute path
            resolved_path = DataPath(path_str)
        elif path_str.startswith('..'):
            # Parent-relative path
            parts = path_str.split('/')
            current = self._main_data_path
            for part in parts:
                if part == '..':
                    current = current.parent
                elif part:
                    current = current / part
            resolved_path = current
        else:
            # Relative path
            resolved_path = self._main_data_path / path_str

        # Get value from tree
        res = tree.get(resolved_path)
        if not res:
            return Result.error(f"DataBag: failed to get '{resolved_path}' from tree", res)

        return Ok(res.unwrapped)

    def get_static(self, key: str, default_value: Any = None) -> Result[Any]:
        """
        Get value strictly from static definition (not from data tree).
        Used for structural fields like event-handlers, style, body, etc.

        Args:
            key: Field name
            default_value: Default value if key not found

        Returns:
            Result with value from static, or default_value if not found
        """
        if self._static is None:
            return Ok(default_value)

        if isinstance(self._static, str):
            # String shorthand (e.g., button: "Click me") - structural fields don't exist
            return Ok(default_value)

        # Dict - look up the key
        value = self._static.get(key, default_value)
        return Ok(value)

    def get(self, key: str, default_value: Any = None) -> Result[Any]:
        """
        Get field value - checks static first, then dynamic from main_data_tree metadata.
        Resolves template references (@path, $tree@path).

        Args:
            key: Field name (e.g., "label")
            default_value: Default value if key not found. If None, returns error.

        Returns:
            Result with field value, or Error if not found and no default
        """
        # Handle string static: treat as "label" value
        if self._static and isinstance(self._static, str):
            if key == "label":
                value = self._static
                # Check if it's a reference
                if self._is_reference(value):
                    return self._resolve_reference(value)
                return Ok(value)
            # For other keys, fall through to tree_like lookup

        # Check if key exists in "head" section (new structure)
        if self._static and isinstance(self._static, dict):
            head = self._static.get("head")
            if head and isinstance(head, dict) and key in head:
                value = head[key]
                # Check if it's a reference
                if self._is_reference(value):
                    return self._resolve_reference(value)
                return Ok(value)

        # Check if key exists directly in static dict (backward compat and for id, etc.)
        if self._static and isinstance(self._static, dict) and key in self._static:
            value = self._static[key]
            # Check if it's a reference
            if self._is_reference(value):
                return self._resolve_reference(value)
            return Ok(value)

        # No static value - try to get from main data tree metadata
        tree = self._data_trees.get(self._main_data_key)
        if not tree:
            if default_value is None:
                return Result.error(f"DataBag.get: no main data tree available and key '{key}' not in static")
            else:
                return Ok(default_value)

        # Get from tree at current path
        full_path = self._main_data_path / key
        res = tree.get(full_path)
        if not res:
            if default_value is None:
                return Result.error(f"DataBag.get: failed to get '{key}' from main_data_tree at path '{full_path}'", res)
            else:
                return Ok(default_value)

        value = res.unwrapped
        # Check if retrieved value is a reference
        if self._is_reference(value):
            return self._resolve_reference(value)

        return Ok(value)

    def get_metadata(self) -> Result[Any]:
        """
        return the metadata view at current path
        """
        tree = self._data_trees.get(self._main_data_key)
        if tree is None:
            if self._static is None:
                return Ok(None)
            if isinstance(self._static, dict):
                return Ok(self._static.copy())
            if isinstance(self._static, str):
                return Ok({"label": self._static})
            return Ok(None)

        res = tree.get_metadata(self._main_data_path)
        if not res:
            return Result.error(f"DataBag.get_metadata: no data found at {self._main_data_path}", res)
        metadata = res.unwrapped.copy()
        if self._static and isinstance(self._static, dict):
            metadata.update(self._static)
        elif self._static and isinstance(self._static, str):
            metadata["label"] = self._static
        return Ok(metadata)

    def set(self, key: str, value: Any) -> Result[None]:
        """
        Set field value - writes to main_data_tree metadata.
        If the static value for key is a reference, writes to the referenced path.

        Args:
            key: Field name (e.g., "label")
            value: Value to set

        Returns:
            Result[None]
        """
        # Check if static has a reference for this key
        if self._static and isinstance(self._static, dict) and key in self._static:
            static_value = self._static[key]
            if self._is_reference(static_value):
                # Parse the reference to get target path
                match = REF_PATTERN.match(static_value)
                if match:
                    tree_name = match.group(1)
                    path_str = match.group(2)

                    # Determine tree
                    if tree_name:
                        tree_key = tree_name[1:]
                        tree = self._data_trees.get(tree_key) if self._data_trees else None
                        if not tree:
                            return Result.error(f"DataBag.set: unknown tree '{tree_key}'")
                        # Named trees (like $local) always use root-relative paths
                        if not path_str.startswith('/'):
                            path_str = '/' + path_str
                    else:
                        tree = self._data_trees.get(self._main_data_key)
                        if not tree:
                            return Result.error(f"DataBag.set: no main data tree available")

                    # Resolve path
                    if path_str.startswith('/'):
                        full_path = DataPath(path_str)
                    elif path_str.startswith('..'):
                        parts = path_str.split('/')
                        current = self._main_data_path
                        for part in parts:
                            if part == '..':
                                current = current.parent
                            elif part:
                                current = current / part
                        full_path = current
                    else:
                        full_path = self._main_data_path / path_str

                    res = tree.set(full_path, value)
                    if not res:
                        return Result.error(f"DataBag.set: failed to set '{key}' at path '{full_path}'", res)
                    return Ok(None)

        # No reference - set at current path in main tree
        tree = self._data_trees.get(self._main_data_key)
        if not tree:
            return Result.error(f"DataBag.set: no main data tree available")

        full_path = self._main_data_path / key
        res = tree.set(full_path, value)
        if not res:
            return Result.error(f"DataBag.set: failed to set '{key}' at path '{full_path}'", res)

        return Ok(None)

    def add_child(self, data: dict) -> Result[None]:
        """
        Add a child to the tree. Handles path resolution and reference resolution.

        Args:
            data: Dict with 'name', 'metadata', and optional 'path'

        Returns:
            Result[None]
        """
        tree = self._data_trees.get(self._main_data_key)
        print(f"DataBag.add_child: input data={data}")
        print(f"DataBag.add_child: main_data_tree={tree}")
        print(f"DataBag.add_child: main_data_path={self._main_data_path}")
        print(f"DataBag.add_child: data_trees keys={list(self._data_trees.keys())}")
        if not tree:
            return Result.error(f"DataBag.add_child: no main data tree available")

        # Resolve references in data
        resolved = {}
        for key, value in data.items():
            if isinstance(value, str) and self._is_reference(value):
                res = self._resolve_reference(value)
                if not res:
                    return Result.error(f"DataBag.add_child: failed to resolve '{key}'", res)
                resolved[key] = res.unwrapped
            elif isinstance(value, dict):
                resolved_dict = {}
                for k, v in value.items():
                    if isinstance(v, str) and self._is_reference(v):
                        res = self._resolve_reference(v)
                        if not res:
                            return Result.error(f"DataBag.add_child: failed to resolve '{k}'", res)
                        resolved_dict[k] = res.unwrapped
                    else:
                        resolved_dict[k] = v
                resolved[key] = resolved_dict
            else:
                resolved[key] = value

        # Get child name
        child_name = resolved.get("name")
        if not child_name:
            return Result.error("DataBag.add_child: missing 'name'")

        # Get metadata
        child_metadata = resolved.get("metadata")
        if child_metadata is None:
            return Result.error("DataBag.add_child: missing 'metadata'")

        # Resolve target path
        path_spec = resolved.get("path")
        if path_spec:
            if path_spec.startswith("/"):
                target_path = DataPath(path_spec)
            else:
                target_path = self._main_data_path / path_spec
        else:
            target_path = self._main_data_path

        print(f"DataBag.add_child: resolved name={child_name}, metadata={child_metadata}, target_path={target_path}")

        res = tree.add_child(target_path, child_name, {"metadata": child_metadata})
        if not res:
            return Result.error(f"DataBag.add_child: failed at '{target_path}'", res)

        return Ok(None)

    def get_children_names(self) -> Result[List[str]]:
        """Get children names at current path from main data tree"""
        tree = self._data_trees.get(self._main_data_key)
        if not tree:
            return Ok([])
        return tree.get_children_names(self._main_data_path)

    def inherit(self, data_path: str = None, static = None) -> Result["DataBag"]:
        """
        Create a child DataBag with inherited/modified path.

        Args:
            data_path: Path for the child (relative, absolute, or $tree@path)
            static: Static params for the child widget

        Supports:
        - relative-path -> current_path / relative-path
        - /absolute/path -> absolute path in main tree
        - ../parent/path -> parent-relative (handled by DataPath)
        - $tree@path -> path in named tree

        Returns:
            Result[DataBag]: New child DataBag
        """
        new_key = self._main_data_key
        new_path = self._main_data_path

        if data_path:
            # Check for named tree reference: $tree@path
            if data_path.startswith('$'):
                match = REF_PATTERN.match(data_path)
                if match:
                    tree_name = match.group(1)  # $tree
                    path_str = match.group(2)   # path after @

                    tree_key = tree_name[1:]  # Remove $ prefix
                    if tree_key not in self._data_trees:
                        return Result.error(f"DataBag.inherit: unknown tree '{tree_key}'")

                    new_key = tree_key
                    # Named trees use root-relative paths
                    if path_str.startswith('/'):
                        new_path = DataPath(path_str)
                    else:
                        new_path = DataPath('/') / path_str
                else:
                    return Result.error(f"DataBag.inherit: invalid tree reference '{data_path}'")
            elif data_path.startswith('/'):
                # Absolute path
                new_path = DataPath(data_path)
            else:
                # Relative path - DataPath handles ..
                new_path = self._main_data_path / data_path

        return DataBag.create(self._data_trees, new_key, new_path, static)
