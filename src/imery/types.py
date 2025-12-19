"""
types shared both by frontend and backend
"""

from abc import ABC, abstractmethod
from .result import Result, Ok
from typing import Union, List, Dict, Any
from .stringcase import spinalcase

from .logging import log

import hashlib, os
import random, string; uid = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

def gen_uid_slow():
    return hashlib.sha1(os.urandom(16)).hexdigest()[:10]

def gen_uid():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

class Object(ABC):
    """
    Any class that is used an the app is subclassing this
    It is enforcing following behaviour:
    1. lifetime
    1.1 any instance is created using create classmethod
    1.2 the create method is calling the constructor that set private members
    1.3.after that the create method is calling the init method
    2. behaviour
    1. each object should have a uinque id
    2. we enforce the uniqueness through their path
    3. each object has a parent object, however the object does not hold reference to the parent object
    4. the path of the current object is the path of the parent plus it's name
    5.
    """
    def __init__(self):
        """Set unique ID for this object"""
        self._uid = f"{spinalcase(self.__class__.__name__)}-{gen_uid()}"
        # print(f"Object: __init__:", self.__class__.__name__, self._uid)

    @abstractmethod
    def init(self) -> Result[None]:
        """Initialize the object - called after __init__ by create()"""
        pass

    @property
    def uid(self):
        return self._uid


    @abstractmethod
    def dispose() -> Result[None]:
        pass

    @classmethod
    def create(cls, *args, **kwargs) -> Result["Object"]:
        obj = cls(*args, **kwargs)

        res = obj.init()
        if not res:
            return Result.error(f"failed to initialize instance {cls.__name__}", res)
        return Ok(obj)

class DataPath:
    """ 
    Each Object in the application has a path in the object hierarchy
    Object may be but must not be registered with the backend
    This allows easy programming of the application and simplifies organizing the backend and frontend
    """
    def __init__(self, path: Union[List[str], str, "DataPath"]):
        if isinstance(path, str):
            if not path.startswith("/"):
                raise Exception(f"Application error, path {path} should start with '/'")
            if path == "/":
                self._path = []
            else:
                self._path = path.split("/")[1:]
        elif isinstance(path, list):
            self._path = path.copy()
        elif path.__class__.__name__ == "DataPath":
            self._path = path.as_list.copy()
        else:
            raise Exception(f"Application error, path {path} should start with '/'")

    @property
    def is_root(self):
        return len(self._path) == 0

    @property
    def as_list(self) -> List[str]:
        return self._path

    def __str__(self):
        return "/" + "/".join(self._path)

    @property
    def name(self):
        return self._path[-1]

    @property
    def namespace(self):
        return self._path[:-1]

    def __truediv__(self, other: str) -> "DataPath":
        if not isinstance(other, str):
            raise ValueError(f"can append only string to DataPath, got {other}, type {type(other)}")

        # If other is an absolute path starting with "/", strip leading "/" and append all segments
        if other.startswith("/"):
            # Strip leading "/" and split into segments
            segments = other[1:].split("/") if other != "/" else []
            result_list = self._path.copy()
            for seg in segments:
                if seg == "..":
                    if result_list:
                        result_list.pop()
                elif seg and seg != ".":
                    result_list.append(seg)
            return DataPath(result_list)

        # If other contains "/" it's a relative path with multiple segments - split and append all
        if "/" in other:
            segments = other.split("/")
            result_list = self._path.copy()
            for seg in segments:
                if seg == "..":
                    if result_list:
                        result_list.pop()
                elif seg and seg != ".":
                    result_list.append(seg)
            return DataPath(result_list)

        # Single segment
        result_list = self._path.copy()
        if other == "..":
            if result_list:
                result_list.pop()
        elif other and other != ".":
            result_list.append(other)
        return DataPath(result_list)

    def __getitem__(self, key: Union[int, slice]) -> Union[str, "NodePath"]:
        if isinstance(key, slice):
            return DataPath(self._path[key])
        else:
            return self._path[key]

    def __len__(self) -> int:
        return len(self._path)

    def __eq__(self, other: Union[str, List[str], "DataPath"]):
        res= self._path == DataPath(other).as_list
        return res


    def __ne__(self, other: Union[str, List[str], "DataPath"]):
        return self._path != DataPath(other).as_list

    def __hash__(self):
        return hash("/" + "/".join(self._path))

    def startswith(self, other: Union[str, "DataPath"]) -> bool:
        if isinstance(other, str):
            return self.startswith(DataPath(other))
        if len(other) > len(self._path):
            return False
        for index, elm in enumerate(other._path):
            if elm != self._path[index]:
                return False
        return True

    def dirname(self) -> "DataPath":
        """Return parent directory (all elements except last)"""
        if len(self._path) == 0:
            return DataPath("/")
        return DataPath(self._path[:-1])

    def filename(self) -> str:
        """Return last element of path (filename)"""
        if len(self._path) == 0:
            return ""
        return self._path[-1]


class TreeLike(ABC):
    """
    Abstract class (interface) for backend elements that provide tree like information
    used by the AssetBrowser visual etc.
    Loading assets is lazy, at least two steps:
    - loading names
    - loading metadata when metadata, or children is requested

    A TreeLike object may be composed of other TreeLike objects

    UI and other elements should always access TreeLike objects through the Waew backend

    All paths (internal-paths) are relative to the provider and start with "/"

    """
    @abstractmethod
    def get_children_names(self, path: DataPath) -> Result[List[str]]:
        """
        Returns the children names for a given internal-path.
        Args:
            path: Internal-path (absoulute path inside the namespace of the provider, starts always with "/")

        Returns:
            List of internal-paths
        """
        raise NotImplementedError("get_children_names not implemented")

    @abstractmethod
    def get_metadata(self, path: DataPath) -> Result[Dict]:
        """
        Returns metadata for a given internal-path.

        Args:
            path: Internal-path (relative to provider, starts with "/")

        Returns:
            Metadata dictionary with "path" field identifying the node
        """
        raise NotImplementedError("get_metadata not implemented")


    @abstractmethod
    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        """
        Returns metadata for a given internal-path.

        Args:
            path: Internal-path (relative to provider, starts with "/")

        Returns:
            Metadata dictionary with "path" field identifying the node
        """
        raise NotImplementedError("get_metadata_keys not implemented")

    @abstractmethod
    def get(self, path: DataPath) -> Result[Any]:
        """
        Returns metadata key value for a given internal-path.

        Args:
            path: Internal-path (relative to provider, starts with "/")

        Returns:
            Metadata dictionary with "path" field identifying the node
        """
        raise NotImplementedError("get_metadata_keys not implemented")

    @abstractmethod
    def set(self, path: DataPath, value: Any) -> Result[None]:
        """
        Sets metadata value for a given internal-path.

        Args:
            path: Internal-path (relative to provider, starts with "/")

        Returns:
            Metadata dictionary with "path" field identifying the node
        """
        raise NotImplementedError("get_metadata_keys not implemented")

    @abstractmethod
    def add_child(self, path: DataPath, name: str, data: Any) -> Result[None]:
        """
        Adds a new child to the node at the given path.

        Args:
            path: Internal-path to the parent node (relative to provider, starts with "/")
            name: Name of the new child
            data: Data for the new child (dict, str, list, TreeLike, or any Python data)

        Returns:
            Result indicating success or failure
        """
        raise NotImplementedError("add_child not implemented")


    @abstractmethod
    def as_tree(self, path: DataPath, depth: int = 0) -> Result[None]:
        raise NotImplementedError("add_child not implemented")




class EventHandler(ABC):
    """
    Interface for objects that handle events from dispatcher
    Events are fire-and-forget (no required responder)
    """

    @abstractmethod
    def handle_event(self, event: dict):
        """
        Handle an event dispatched to this handler

        Args:
            event: Dictionary with event details
                Required fields:
                - "event": event name/type
                Optional fields:
                - "data": event payload
                - "source-id": originating component
        """
        pass


class ActionHandler(ABC):
    """
    Interface for objects that handle actions from dispatcher
    Actions require at least one responder
    """

    def __init__(self, dispatcher: "Dispatcher"):
        self._dispatcher = dispatcher

    def init(self) -> Result[None]:
        return self._dispatcher.register_action_handler(self)


    @abstractmethod
    def handle_action(self, action: dict):
        """
        Handle an action dispatched to this handler

        Args:
            action: Dictionary with action details
                Required fields:
                - "action": action name/type
                Optional fields:
                - "data": action payload
                - "target-id": target component
        """
        pass


class DataBag(Object):
    """ Abstraction used to pass data to the Widgets
    It has a main TreeLike and secondary TreeLike instances specified in the layouts
    """
    def __init__(self):
        pass

