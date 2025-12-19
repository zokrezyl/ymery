"""Waveform Generator - Generates standard waveforms (sine, square, triangle) with ring buffer"""
import threading
import numpy as np
import time

from imery.backend.types import AudioDeviceManager, AudioDevice
from imery.types import DataPath
from imery.backend.audio_buffer import DynamicAudioRingBuffer, DynamicAudioBufferMediator, MediatedAudioBuffer
from imery.result import Result, Ok

from typing import List, Dict, Any, Union
from imery.decorators import device_manager, device


@device
class WaveformDevice(AudioDevice, threading.Thread):
    """Generates waveform data in a ring buffer"""

    def __init__(self, waveform_type: str, sample_rate: int = 48000, frequency: float = 440.0, period_size: int = 1024):
        """
        Args:
            waveform_type: Type of waveform ("sine", "square", "triangle")
            sample_rate: Sample rate in Hz
            frequency: Waveform frequency in Hz
            period_size: Number of samples to generate per period
        """
        AudioDevice.__init__(self)
        threading.Thread.__init__(self)
        self.daemon = True  # Thread will exit when main program exits

        self._waveform_type = waveform_type
        self._sample_rate = sample_rate
        self._frequency = frequency
        self._period_size = period_size
        self._buffer_mediator = None
        self._phase = 0.0  # Current phase for continuous waveform generation
        self._sample_buffer = np.zeros(period_size, dtype=np.float32)  # Preallocated buffer

    def init(self) -> Result[None]:
        """Initialize ring buffer and mediator"""
        # Create single-channel ring buffer
        res = DynamicAudioRingBuffer.create(
            sample_rate=self._sample_rate,
            initial_size=0,  # Lazy allocation
            period_size=self._period_size,
            format_type=np.float32
        )
        if not res:
            return Result.error(f"WaveformDevice: failed to create DynamicRingBuffer")

        dynamic_ring_buffer = res.unwrapped

        res = DynamicAudioBufferMediator.create(dynamic_ring_buffer)
        if not res:
            return Result.error(f"WaveformDevice: failed to create DynamicBufferMediator")

        self._buffer_mediator = res.unwrapped
        return Ok(None)

    def open(self, path: DataPath, config: dict) -> Result[MediatedAudioBuffer]:
        """Open a mediated buffer.

        Args:
            path: DataPath (should be root for single-channel device)
            config: Configuration dict

        Returns:
            Result containing MediatedAudioBuffer
        """
        if not self._buffer_mediator:
            return Result.error("WaveformDevice: buffer mediator not initialized")

        return self._buffer_mediator.open()

    def dispose(self) -> Result[None]:
        """Stop generation and clean up"""
        self.stop()
        return Ok(None)

    def _generate_waveform(self):
        """Generate waveform samples directly into preallocated buffer."""
        # Calculate phase increment per sample
        phase_increment = 2.0 * np.pi * self._frequency / self._sample_rate

        # Generate phase values - multiply operation writes directly to buffer
        np.multiply(np.arange(self._period_size, dtype=np.float32), phase_increment, out=self._sample_buffer)
        np.add(self._sample_buffer, self._phase, out=self._sample_buffer)

        # Update phase for next call (keep in [0, 2π] range)
        self._phase = (self._phase + self._period_size * phase_increment) % (2.0 * np.pi)

        # Generate waveform based on type, writing directly to buffer
        if self._waveform_type == "sine":
            np.sin(self._sample_buffer, out=self._sample_buffer)
        elif self._waveform_type == "square":
            np.sin(self._sample_buffer, out=self._sample_buffer)
            np.sign(self._sample_buffer, out=self._sample_buffer)
        elif self._waveform_type == "triangle":
            # Triangle wave: -1 to 1
            # Normalize phase to [0, 1] and take fractional part
            np.divide(self._sample_buffer, 2.0 * np.pi, out=self._sample_buffer)
            np.remainder(self._sample_buffer, 1.0, out=self._sample_buffer)
            # Convert to triangle: 2 * abs(2 * x - 1) - 1
            np.multiply(self._sample_buffer, 2.0, out=self._sample_buffer)
            np.subtract(self._sample_buffer, 1.0, out=self._sample_buffer)
            np.abs(self._sample_buffer, out=self._sample_buffer)
            np.multiply(self._sample_buffer, 2.0, out=self._sample_buffer)
            np.subtract(self._sample_buffer, 1.0, out=self._sample_buffer)

    def run(self):
        while True:
            #print("WaveformDevice: run")
            """Generate waveform data continuously"""
            # Generate one period of samples (writes to self._sample_buffer)
            self._generate_waveform()

            # Write to ring buffer
            self._buffer_mediator.backend.write(self._sample_buffer)

            # Sleep to simulate real-time (period duration)
            sleep_time = self._period_size / self._sample_rate
            time.sleep(sleep_time)


    def stop(self):
        """Stop waveform generation"""
        if self.is_alive():
            self.join(timeout=1.0)

    def get_children_names(self, path: DataPath) -> Result[List[str]]:
        """Get children for browsing.

        Args:
            path: Internal path (relative to device)

        Returns:
            Result[List[str]]
        """
        # Root only - no children
        if len(path) == 0 or str(path) == "/":
            return Ok([])

        return Ok([])

    def get_metadata(self, path: DataPath) -> Result[Dict]:
        """Get metadata for this device.

        Args:
            path: Internal path (relative to device)

        Returns:
            Result[Dict]
        """
        # Root metadata
        if len(path) == 0 or str(path) == "/":
            meta = {
                "uid": self.uid,
                "label": f"{self._waveform_type.capitalize()} ({self._frequency}Hz)",
                "type": "waveform-device",
                "category": "audio-device",
                "status": "running" if self.is_alive() else "stopped",
                "capabilities": {
                    "openable": False,
                    "configurable": True,
                    "closeable": True,
                    "readable": True,
                    "writable": False
                },
                "details": {
                    "waveform-type": self._waveform_type,
                    "frequency": self._frequency,
                    "sample-rate": self._sample_rate,
                    "period-size": self._period_size
                }
            }
            # Add buffer mediator as instance
            if self._buffer_mediator:
                meta["instance"] = self._buffer_mediator
            return Ok(meta)

        return Result.error(f"WaveformDevice: unknown path {path}")

    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        """Get metadata keys using existing get_metadata"""
        res = self.get_metadata(path)
        if not res:
            return Result.error(f"WaveformDevice: failed to get metadata for {path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            return Ok(list(metadata.keys()))
        return Result.error(f"WaveformDevice: metadata is not a dict at {path}")

    def get(self, path: DataPath) -> Result:
        """Get metadata value - last component of path is the key"""
        node_path = path.dirname()
        key = path.filename()

        res = self.get_metadata(node_path)
        if not res:
            return Result.error(f"WaveformDevice: failed to get metadata for {node_path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            if key in metadata:
                return Ok(metadata[key])
            return Result.error(f"WaveformDevice: key '{key}' not found in metadata at {node_path}")
        return Result.error(f"WaveformDevice: metadata is not a dict at {node_path}")

    def set(self, path: DataPath, value) -> Result[None]:
        """Set not implemented"""
        return Result.error("WaveformDevice: set: not implemented")

    def add_child(self, path: DataPath, value) -> Result[None]:
        """Set not implemented"""
        return Result.error("WaveformDevice: add_child: not implemented")

    def as_tree(self, data_path: DataPath = None, depth: int = 0) -> Result[Union[dict]]:
        pass

@device_manager
class WaveformManager(AudioDeviceManager):
    """Manager for waveform generators"""

    WAVEFORMS = ["sine", "square", "triangle"]

    def __init__(self):
        super().__init__()
        self._waveform_devices = {}  # Track opened WaveformDevice instances

    def init(self) -> Result[None]:
        """Initialize waveform manager"""
        return Ok(None)

    def configure(self, config: dict) -> Result[None]:
        """Configure waveform manager"""
        return Ok(None)

    def dispose(self) -> Result[None]:
        """Clean up all waveform devices"""
        for path, device in self._waveform_devices.items():
            device.stop()
        self._waveform_devices.clear()
        return Ok(None)

    def get_children_names(self, path: DataPath) -> Result[List[str]]:
        """Get children for browsing.

        Args:
            path: Path relative to this provider

        Returns:
            Result[List[str]]
        """
        # Root: "/" -> return available and opened branches
        if len(path) == 0 or str(path) == "/":
            return Ok(["available", "opened"])

        # Handle /available and /opened branches
        if len(path) > 0 and path[0] in ["available", "opened"]:
            branch = path[0]
            subpath = path[1:]  # Strip branch prefix

            if branch == "available":
                return self._get_children_names_available(subpath)
            else:
                return self._get_children_names_opened(subpath)

        return Result.error(f"WaveformManager: unknown path {path}")

    def _get_children_names_available(self, path: DataPath) -> Result[List[str]]:
        """Get children for /available branch"""
        # Root: "/" -> return waveform types
        if len(path) == 0 or str(path) == "/":
            return Ok(self.WAVEFORMS)

        # Individual waveform: "/sine", "/square", "/triangle" -> return "0" (single channel)
        if len(path) == 1 and path[0] in self.WAVEFORMS:
            return Ok(["0"])

        return Ok([])

    def _get_children_names_opened(self, path: DataPath) -> Result[List[str]]:
        """Get children for /opened branch - delegates to devices"""
        # Root: "/" -> return opened waveforms
        if len(path) == 0 or str(path) == "/":
            if len(self._waveform_devices) > 0:
                return Ok([path[0] for path in self._waveform_devices.keys()])
            return Ok([])

        # "/sine", "/square", etc. -> delegate to device
        if len(path) >= 1 and path[0] in self.WAVEFORMS:
            device_path = DataPath("/" + path[0])
            device = self._waveform_devices.get(device_path)
            if not device:
                return Result.error(f"WaveformManager: device at {device_path} is not opened")

            # Delegate to device
            subpath = DataPath(path.as_list[1:]) if len(path) > 1 else DataPath("/")
            return device.get_children_names(subpath)

        return Ok([])

    def get_metadata(self, path: DataPath) -> Result[Dict]:
        """Get metadata for a path.

        Args:
            path: Path relative to this provider

        Returns:
            Result[Dict]
        """
        # Root
        if len(path) == 0 or str(path) == "/":
            return Ok({
                "uid": self.uid,
                "name": "waveform",
                "label": "Waveform Generator",
                "type": "waveform-manager",
                "category": "audio-device-manager",
                "description": "Generates standard waveforms (sine, square, triangle)"
            })

        # /available or /opened folder
        if len(path) == 1 and path[0] in ["available", "opened"]:
            return Ok({
                "name": path[0],
                "label": path[0].capitalize(),
                "type": "folder",
                "category": "folder"
            })

        # Handle /available and /opened branches
        if len(path) > 0 and path[0] in ["available", "opened"]:
            branch = path[0]
            subpath = path[1:]  # Strip branch prefix

            if branch == "available":
                return self._get_metadata_available(subpath)
            else:
                return self._get_metadata_opened(subpath)

        return Result.error(f"WaveformManager: unknown path {path}")

    def _get_metadata_available(self, path: DataPath) -> Result[Dict]:
        """Get metadata for /available branch"""
        # Individual waveform endpoint: "/sine", "/square", "/triangle"
        if len(path) == 1 and path[0] in self.WAVEFORMS:
            waveform_type = path[0]
            return Ok({
                "name": waveform_type,
                "label": f"{waveform_type.capitalize()} Wave",
                "type": "waveform-device",
                "category": "audio-device",
                "description": f"{waveform_type.capitalize()} waveform generator",
                "capabilities": {
                    "openable": True,
                    "readable": True,
                    "writable": False
                },
                "details": {
                    "waveform-type": waveform_type
                },
                "config-schema": {
                    "frequency": {
                        "type": "float",
                        "default": 440.0,
                        "min": 20.0,
                        "max": 20000.0,
                        "label": "Frequency (Hz)"
                    },
                    "sample-rate": {
                        "type": "int",
                        "default": 48000,
                        "choices": [44100, 48000, 96000],
                        "label": "Sample Rate"
                    },
                    "period-size": {
                        "type": "int",
                        "default": 1024,
                        "min": 128,
                        "max": 8192,
                        "label": "Period Size"
                    }
                }
            })

        # Channel path: "/sine/0", "/square/0", "/triangle/0" - hardcoded, no device created
        if len(path) == 2 and path[0] in self.WAVEFORMS and path[1] == "0":
            waveform_type = path[0]
            return Ok({
                "name": "0",
                "label": "Channel 0",
                "type": "audio-channel",
                "category": "audio-channel",
                "capabilities": {
                    "openable": True,
                    "readable": True,
                    "writable": False
                },
                "details": {
                    "channel-id": 0,
                    "waveform-type": waveform_type
                }
            })

        return Result.error(f"WaveformManager: unknown available path {path}")

    def _get_metadata_opened(self, path: DataPath) -> Result[Dict]:
        """Get metadata for /opened branch - delegates to devices"""
        # Individual opened waveform: "/sine", "/square", "/triangle"
        if len(path) == 1 and path[0] in self.WAVEFORMS:
            device_path = DataPath("/" + path[0])
            device = self._waveform_devices.get(device_path)
            if not device:
                return Result.error(f"WaveformManager: device at {device_path} is not opened")

            # Return device root metadata
            return device.get_metadata(DataPath("/"))

        # Deeper paths - delegate to device
        if len(path) >= 2 and path[0] in self.WAVEFORMS:
            device_path = DataPath("/" + path[0])
            device = self._waveform_devices.get(device_path)
            if not device:
                return Result.error(f"WaveformManager: device at {device_path} is not opened")

            # Delegate to device
            subpath = DataPath(path.as_list[1:])
            return device.get_metadata(subpath)

        return Result.error(f"WaveformManager: unknown opened path {path}")

    def open(self, path: DataPath, config: dict) -> Result:
        """Open a waveform channel.

        Args:
            path: Path to channel (e.g., "/available/sine/0")
            config: Configuration (frequency, sample_rate, etc.)

        Returns:
            Result containing MediatedBuffer
        """
        # Path should be "/available/waveform_type/0" (channel path)
        if len(path) != 3 or path[0] != "available" or path[1] not in self.WAVEFORMS or path[2] != "0":
            return Result.error(f"WaveformManager: invalid channel path {path}, expected /available/waveform_type/0")

        waveform_type = path[1]
        device_path = DataPath("/" + waveform_type)

        # Check if device already opened
        if device_path not in self._waveform_devices:
            # Extract config
            frequency = config.get("frequency", 440.0)
            sample_rate = config.get("sample_rate", 48000)
            period_size = config.get("period_size", 1024)

            # Create device using create pattern
            res = WaveformDevice.create(
                waveform_type=waveform_type,
                sample_rate=sample_rate,
                frequency=frequency,
                period_size=period_size
            )
            if not res:
                return Result.error(f"WaveformManager: failed to create {waveform_type} device", res)

            device = res.unwrapped

            # Start generation thread
            device.start()

            # Store device
            self._waveform_devices[device_path] = device

        # Get device and open channel
        device = self._waveform_devices[device_path]
        return device.open(DataPath("/"), config)

    def close(self, path: DataPath) -> Result[None]:
        """Close a waveform generator.

        Args:
            path: Path to waveform device

        Returns:
            Result[None]
        """
        if path not in self._waveform_devices:
            return Result.error(f"WaveformManager: device at {path} not opened")

        device = self._waveform_devices[path]
        device.stop()
        del self._waveform_devices[path]

        return Ok(None)

    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        """Get metadata keys using existing get_metadata"""
        res = self.get_metadata(path)
        if not res:
            return Result.error(f"WaveformManager: failed to get metadata for {path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            return Ok(list(metadata.keys()))
        return Result.error(f"WaveformManager: metadata is not a dict at {path}")

    def get(self, path: DataPath) -> Result[Any]:
        """Get metadata value - last component of path is the key"""
        node_path = path.dirname()
        key = path.filename()

        res = self.get_metadata(node_path)
        if not res:
            return Result.error(f"WaveformManager: failed to get metadata for {node_path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            if key in metadata:
                return Ok(metadata[key])
            return Result.error(f"WaveformManager: key '{key}' not found in metadata at {node_path}")
        return Result.error(f"WaveformManager: metadata is not a dict at {node_path}")

    def set(self, path: DataPath, value) -> Result[None]:
        """Set not implemented"""
        return Result.error("WaveformManager: set: not implemented")

    def add_child(self, path: DataPath, value) -> Result[None]:
        """Set not implemented"""
        return Result.error("WaveformManager: add_child: not implemented")

    def as_tree(self, data_path: DataPath = None, depth: int = 0) -> Result[Union[dict]]:
        pass

def main():
    res = WaveformManager.create()

    if not res:
        print("error: ", res)
    manager = res.unwrapped

    res = manager.get_children_names(DataPath("/available/sine"))
    if not res:
        print("error: ", res)

    print(res.unwrapped)

    res = manager.get_metadata(DataPath("/available/sine/0"))

    if not res:
        print("error: ", res)
    metadata = res.unwrapped

    print(metadata)

    pass

if __name__ == "__main__":
    main()
