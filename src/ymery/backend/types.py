from ymery.types import Object, DataPath, TreeLike
from ymery.result import Result, Ok

from typing import List, Dict, Union, Any

from abc import ABC, abstractmethod

class Buffer(Object):
    pass


class ChannelId(ABC):
    """
    channel id abstraction
    while alsa, file buffer have int as ID, jack for instance uses a string
    """
    @property
    @abstractmethod
    def label(self):
        pass

class Device(Object, TreeLike):
    """
    Abstract base class for a data source that can provide buffers/channels
    A Device may provide several audio channels.
    It is tree like as it should provide browsing capabilities
    """

    @abstractmethod
    def open(self, channel_id: ChannelId, config: dict) -> Result[Buffer]:
        """Get the buffer mediator for this provider.

        Returns:
            BufferMediator instance (DynamicBufferMediator or StaticBufferMediator)
        """
        pass

class AudioDevice(Device):
    """
    Abstract base class for an audio data source.
    A provider may provide several audio channels.
    It is tree like as it should provide browsing capabilities
    """


class DeviceManagerLike(ABC):
    """
    Abstract class (interface) for audio source lifecycle management.
    Manages creation, updating, and deletion of assets (connections, buffers, etc.).

    Assets can be hierarchical:
    - Connection assets (e.g., AlsaProvider for ALSA device)
    - Buffer assets (e.g., individual channels within a connection)

    All paths are DataPath instances relative to the component's namespace.
    """

    @abstractmethod
    def open(self, path: DataPath, params: Dict) -> Result[Union[AudioDevice, Buffer]]:
        """
        Create/open an asset at the given path with specified parameters.

        Args:
            path: DataPath where asset should be created
            params: Dictionary of parameters (from constructor-arguments metadata)

        Returns:
            Result containing the created asset (Provider, buffer, etc.)
        """
        raise NotImplementedError("create_asset not implemented")

    @abstractmethod
    def configure(self, path: DataPath, params: Dict) -> Result[None]:
        """
        Update parameters of an existing asset.

        Args:
            path: DataPath to the asset
            params: Dictionary of parameters to update

        Returns:
            Result[None] indicating success or failure
        """
        raise NotImplementedError("update_asset not implemented")

    @abstractmethod
    def close(self, path: DataPath) -> Result[None]:
        """
        Delete/close an asset at the given path.

        Args:
            path: DataPath to the asset

        Returns:
            Result[None] indicating success or failure
        """
        raise NotImplementedError("delete_asset not implemented")


class DeviceManager(Object, TreeLike, DeviceManagerLike):
    """
    Abstracts a device manager (alsa, jack, soundfile, wave)
    A device manager returns metadata tree about the available assets
    For a specific asset it returns the arguments that can be fed to the "create" method of the provider itself
    """
    def __init__(self):
        super().__init__()


class AudioDeviceManager(DeviceManager):
    """
    Abstracts a device manager (alsa, jack, soundfile, wave)
    A device manager returns metadata tree about the available assets
    For a specific asset it returns the arguments that can be fed to the "create" method of the provider itself
    """
    def __init__(self):
        super().__init__()


class TreeLikeCache(ABC):
    """
    Cache for the assetprovider browsing interface with TTL support
    """
    def __init__(self, ttl: float = 10.0):
        self._children = {}
        self._metadata = {}
        self._ttl = ttl  # Time-to-live in seconds
        self._cache_timestamp = None  # When cache was last populated
        import time
        self._time = time  # Store time module for testing

    def _is_cache_expired(self) -> bool:
        """Check if cache has expired based on TTL"""
        if self._cache_timestamp is None:
            return True
        if self._ttl is None:
            return False
        elapsed = self._time.time() - self._cache_timestamp
        return elapsed >= self._ttl

    def get_children_names(self, path: DataPath) -> Result[List[str]]:
        assert isinstance(path, DataPath)
        # Check TTL and invalidate if expired
        if self._is_cache_expired():
            self.invalidate_cache()

        res = self._children.get(path)
        if res is None:
            res = self.get_children_names_uncached(path)
            # Cache the Result (both Ok and Err)
            self._children[path] = res
            # Update timestamp on first cache entry
            if self._cache_timestamp is None:
                self._cache_timestamp = self._time.time()
            if not res:
                return Result.error(f"TreeLikeCache: could not retrive children for {path}", res)
            return res
        # Return cached Result
        if not res:
            return Result.error(f"TreeLikeCache: cached error for {path}", res)
        return res

    def get_metadata(self, path: DataPath) -> Result[Dict]:
        assert isinstance(path, DataPath)
        # Check TTL and invalidate if expired
        if self._is_cache_expired():
            self.invalidate_cache()

        res = self._metadata.get(path)
        if res is None:
            res = self.get_metadata_uncached(path)
            # Cache the Result (both Ok and Err)
            self._metadata[path] = res
            # Update timestamp on first cache entry
            if self._cache_timestamp is None:
                self._cache_timestamp = self._time.time()
            if not res:
                return Result.error(f"TreeLikeCache: could not retrieve metadata for {path}", res)
            return res
        # Return cached Result
        if not res:
            return Result.error(f"TreeLikeCache: cached error for {path}", res)
        return res

    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        """Get metadata keys by retrieving full metadata and extracting keys"""
        assert isinstance(path, DataPath)
        # Check if metadata is already cached
        cached_metadata = self._metadata.get(path)
        if cached_metadata is not None:
            # Metadata already retrieved
            if not cached_metadata:
                return Result.error(f"TreeLikeCache: cached error for {path}", cached_metadata)
            metadata = cached_metadata.unwrapped
            if isinstance(metadata, dict):
                return Ok(list(metadata.keys()))
            return Result.error(f"TreeLikeCache: metadata is not a dict at {path}")

        # Not cached - retrieve full metadata
        res = self.get_metadata(path)
        if not res:
            return Result.error(f"TreeLikeCache: could not retrieve metadata for {path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            return Ok(list(metadata.keys()))
        return Result.error(f"TreeLikeCache: metadata is not a dict at {path}")

    def get(self, path: DataPath) -> Result[Any]:
        """Get metadata value - last component of path is the key"""
        assert isinstance(path, DataPath)
        node_path = path.dirname()
        key = path.filename()

        # Check if metadata is already cached
        cached_metadata = self._metadata.get(node_path)
        if cached_metadata is not None:
            # Metadata already retrieved
            if not cached_metadata:
                return Result.error(f"TreeLikeCache: cached error for {node_path}", cached_metadata)
            metadata = cached_metadata.unwrapped
            if isinstance(metadata, dict):
                if key in metadata:
                    return Ok(metadata[key])
                return Result.error(f"TreeLikeCache: key '{key}' not found in metadata at {node_path}")
            return Result.error(f"TreeLikeCache: metadata is not a dict at {node_path}")

        # Not cached - retrieve full metadata
        res = self.get_metadata(node_path)
        if not res:
            return Result.error(f"TreeLikeCache: could not retrieve metadata for {node_path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            if key in metadata:
                return Ok(metadata[key])
            return Result.error(f"TreeLikeCache: key '{key}' not found in metadata at {node_path}")
        return Result.error(f"TreeLikeCache: metadata is not a dict at {node_path}")

    def set(self, path: DataPath, value: Any) -> Result[None]:
        """Set not implemented for cache"""
        return Result.error("TreeLikeCache: set not implemented")

    def invalidate_cache(self):
        """Invalidate the entire cache - to be called when data changes"""
        self._children.clear()
        self._metadata.clear()
        self._cache_timestamp = None

    def erase_cache(self):
        """Deprecated: use invalidate_cache() instead"""
        self.invalidate_cache()

    @abstractmethod
    def get_children_names_uncached(self, path: DataPath) -> Result[List[str]]:
        pass

    @abstractmethod
    def get_metadata_uncached(self, path: DataPath) -> Result[Dict]:
        pass

