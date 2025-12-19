"""Soundfile Device - Audio file handling via libsndfile"""
import numpy as np
try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    sf = None
    SOUNDFILE_AVAILABLE = False
import os

from imery.backend.types import AudioDevice
from imery.types import DataPath
from imery.backend.audio_buffer import FileAudioBuffer, StaticAudioBufferMediator
from imery.decorators import device

from imery.result import Result, Ok

from typing import Union


class SoundfileBuffer(FileAudioBuffer):
    """FileAudioBuffer specialized for soundfiles - single channel only.

    This is a simple wrapper that adds lazy loading support.
    One buffer per channel - SoundfileProvider creates multiple instances.
    """

    def __init__(self, file_path: str, channel_data: np.ndarray, sample_rate: int, channel_id: str, full_load: bool = True):
        """Initialize soundfile buffer for a single channel.

        Args:
            file_path: Path to audio file
            channel_data: 1D numpy array for this channel (contiguous)
            sample_rate: Sample rate in Hz
            channel_id: Channel ID string (for identification)
            full_load: If True, keep full buffer; if False, allow dynamic range loading
        """
        self._sf_file_path = file_path
        self._channel_id = channel_id
        self._full_load = full_load

        # Initialize parent with single-channel data
        super().__init__(file_path=file_path, data=channel_data, sample_rate=sample_rate)

    def init(self) -> Result[None]:
        pass

    def update(self):
        """Update buffer (no-op for static files)."""
        pass

    def dispose(self):
        pass


@device
class SoundfileDevice(AudioDevice):
    """File-based audio device with per-channel buffers.

    Args:
        file_path: Path to audio file
        full_load: If True, load entire file and keep in memory
    """

    def __init__(self, file_path, full_load=True):
        AudioDevice.__init__(self)
        self._file_path = file_path
        self._full_load = full_load

    def init(self) -> Result[None]:
        if not SOUNDFILE_AVAILABLE:
            return Result.error("SoundfileDevice: soundfile library not available")
        # Get metadata from file
        with sf.SoundFile(str(self._file_path), mode='r') as audio_file:
            self._channels = audio_file.channels
            self._sr = audio_file.samplerate
            self._frames = len(audio_file)

        # Read interleaved data from disk once
        data, _ = sf.read(self._file_path, dtype='float32')

        # Handle mono vs stereo
        if len(data.shape) == 1:
            # Mono: reshape to (frames, 1)
            data = data.reshape(-1, 1)
        # data is now (frames, channels) - interleaved

        # Store channel data as dictionary keyed by DataPath
        self._channel_data = {}
        for ch in range(self._channels):
            channel_path = DataPath(f"/{ch}")
            # Extract contiguous 1D array for this channel
            channel_data = np.ascontiguousarray(data[:, ch])
            self._channel_data[channel_path] = channel_data

        # Discard interleaved data
        del data

        # Create one buffer mediator per channel (wraps file buffer)
        # Dictionary keyed by DataPath (e.g., DataPath("/0"))
        self._buffer_mediators = {}
        for channel_path in self._channel_data.keys():
            # Create FileAudioBuffer for this channel
            file_buffer = SoundfileBuffer(
                file_path=self._file_path,
                channel_data=self._channel_data[channel_path],
                sample_rate=self._sr,
                channel_id=str(channel_path),
                full_load=self._full_load
            )

            # Create mediator for this channel
            res = StaticAudioBufferMediator.create(file_buffer)
            if not res:
                return Result.error("SoundfileDevice: init: could not create StaticAudioBufferMediator", res)
            mediator = res.unwrapped
            self._buffer_mediators[channel_path] = mediator

        mode = "full_load" if self._full_load else "dynamic"
        print(f"SoundfileDevice: Opened {self._file_path} ({mode}) - {self._channels} channels @ {self._sr}Hz")
        return Ok(None)

    def open(self, path: DataPath, config: dict) -> Result:
        """Open a channel buffer with specified config (range).

        Args:
            path: DataPath to channel (e.g., DataPath("/0"))
            config: Dictionary with 'start' and 'length' for buffer range

        Returns:
            Result containing MediatedBuffer from StaticAudioBufferMediator
        """
        if path not in self._buffer_mediators:
            return Result.error(f"Channel {path} not found")

        # Get mediator and open new mediated buffer
        mediator = self._buffer_mediators[path]

        # Open returns a new MediatedBuffer with the specified range
        start = config.get('start', 0)
        length = config.get('length', len(self._channel_data[path]))
        mediated_buffer = mediator.open(start, length)

        print(f"SoundfileDevice: Opened channel {path}, range [{start}:{start+length}]")
        return Ok(mediated_buffer)

    def get_children_names(self, path: DataPath):
        """Get children for browsing this device's structure.

        Args:
            path: Internal-path (relative to device)

        Returns:
            Result[List[str]]
        """
        # Root: "/" -> return list of channel IDs
        if len(path) == 0 or path == "/":
            return Ok([str(i) for i in range(self._channels)])

        return Ok([])

    def get_metadata(self, path: DataPath):
        """Get metadata for a node in this device's tree.

        Args:
            path: Internal-path (relative to device)

        Returns:
            Result[Dict]
        """
        # Root: "/"
        if len(path) == 0 or path == "/":
            return Ok({
                "uid": self.uid,
                "name": os.path.basename(self._file_path),
                "label": os.path.basename(self._file_path),
                "type": "soundfile-device",
                "category": "audio-device",
                "status": "opened",
                "capabilities": {
                    "openable": False,
                    "configurable": False,
                    "closeable": True,
                    "readable": True,
                    "writable": False
                },
                "details": {
                    "file-path": self._file_path,
                    "channels": self._channels,
                    "sample-rate": self._sr,
                    "frames": self._frames
                }
            })

        # Individual channel "0", "1", etc.
        if len(path) == 1:
            if path in self._buffer_mediators:
                mediator = self._buffer_mediators.get(path)
                meta = {
                    "name": path[0],
                    "label": f"Channel {path[0]}",
                    "type": "audio-channel",
                    "category": "audio-channel",
                    "status": "active",
                    "capabilities": {
                        "openable": False,
                        "closeable": True,
                        "readable": True,
                        "writable": False
                    },
                    "details": {
                        "channel-id": path[0]
                    }
                }
                # Add instance if mediator exists
                if mediator:
                    meta["instance"] = mediator
                    meta["uid"] = mediator.uid if hasattr(mediator, 'uid') else f"channel-{self.uid[:8]}-{path[0]}"
                return Ok(meta)

        return Result.error(f"SoundfileDevice: unknown path {path}")

    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        """Get metadata keys using existing get_metadata"""
        res = self.get_metadata(path)
        if not res:
            return Result.error(f"SoundfileDevice: failed to get metadata for {path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            return Ok(list(metadata.keys()))
        return Result.error(f"SoundfileDevice: metadata is not a dict at {path}")

    def get(self, path: DataPath) -> Result:
        """Get metadata value - last component of path is the key"""
        node_path = path.dirname()
        key = path.filename()

        res = self.get_metadata(node_path)
        if not res:
            return Result.error(f"SoundfileDevice: failed to get metadata for {node_path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            if key in metadata:
                return Ok(metadata[key])
            return Result.error(f"SoundfileDevice: key '{key}' not found in metadata at {node_path}")
        return Result.error(f"SoundfileDevice: metadata is not a dict at {node_path}")

    def set(self, path: DataPath, value) -> Result[None]:
        """Set not implemented"""
        return Result.error("SoundfileDevice: set: not implemented")

    def add_child(self, path: DataPath, value) -> Result[None]:
        """Set not implemented"""
        return Result.error("SoundfileDevice: add_child: not implemented")

    def as_tree(self, data_path: DataPath = None, depth: int = 0) -> Result[Union[dict]]:
        pass

    def dispose(self):
        pass
