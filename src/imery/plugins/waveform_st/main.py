"""Waveform Generator (Single-Threaded) - For Pyodide/WebAssembly environments"""
import numpy as np
import time

from imery.backend.types import AudioDeviceManager, AudioDevice
from imery.types import DataPath
from imery.backend.audio_buffer import DynamicAudioRingBuffer, DynamicAudioBufferMediator, MediatedAudioBuffer
from imery.result import Result, Ok

from typing import List, Dict, Any, Union, Callable, Optional
from imery.decorators import device_manager, device


class OnDemandAudioRingBuffer(DynamicAudioRingBuffer):
    """
    Ring buffer that generates samples on-demand when data is accessed.

    Instead of a separate thread writing samples continuously,
    this buffer calculates elapsed time and generates missing samples
    when the data property is accessed.
    """

    def __init__(self, sample_rate: int, initial_size: int = 0,
                 period_size: Optional[int] = None, format_type: type = np.float32,
                 generator: Optional[Callable[[], np.ndarray]] = None):
        """Initialize on-demand ring buffer.

        Args:
            sample_rate: Sample rate in Hz
            initial_size: Initial logical buffer size in samples (0 for minimal)
            period_size: Period size for rounding (optional)
            format_type: Numpy data type for samples
            generator: Callable that returns period_size samples when called
        """
        super().__init__(sample_rate, initial_size, period_size, format_type)
        self._generator = generator
        self._start_time: Optional[float] = None
        self._samples_generated: int = 0
        self._running: bool = False

    def start(self):
        """Start the virtual clock for on-demand generation."""
        self._start_time = time.time()
        self._samples_generated = 0
        self._running = True

    def stop(self):
        """Stop on-demand generation."""
        self._running = False

    def lock(self):
        """No-op for single-threaded."""
        pass

    def unlock(self):
        """No-op for single-threaded."""
        pass

    def try_lock(self) -> bool:
        """No-op for single-threaded."""
        return True

    def _update(self):
        """Generate missing samples based on elapsed time."""
        if not self._running or self._start_time is None or self._generator is None:
            return

        # Calculate expected samples based on elapsed time
        elapsed = time.time() - self._start_time
        expected_samples = int(elapsed * self._sample_rate)

        # Generate missing samples in period_size chunks
        while self._samples_generated + self._period_size <= expected_samples:
            samples = self._generator()
            self.write(samples)
            self._samples_generated += self._period_size

    @property
    def data(self) -> Optional[np.ndarray]:
        """Get buffer data, generating missing samples first.

        Returns:
            Numpy view of useful data (most recent samples ending at ptr),
            or None if not allocated
        """
        self._update()
        return super().data


@device
class WaveformDeviceST(AudioDevice):
    """Single-threaded waveform generator for Pyodide/WebAssembly environments."""

    def __init__(self, waveform_type: str, sample_rate: int = 48000,
                 frequency: float = 440.0, period_size: int = 1024):
        """
        Args:
            waveform_type: Type of waveform ("sine", "square", "triangle")
            sample_rate: Sample rate in Hz
            frequency: Waveform frequency in Hz
            period_size: Number of samples to generate per period
        """
        AudioDevice.__init__(self)

        self._waveform_type = waveform_type
        self._sample_rate = sample_rate
        self._frequency = frequency
        self._period_size = period_size
        self._buffer_mediator = None
        self._ring_buffer = None
        self._phase = 0.0
        self._sample_buffer = np.zeros(period_size, dtype=np.float32)

    def init(self) -> Result[None]:
        """Initialize ring buffer and mediator."""
        # Create on-demand ring buffer with generator callback
        res = OnDemandAudioRingBuffer.create(
            sample_rate=self._sample_rate,
            initial_size=0,
            period_size=self._period_size,
            format_type=np.float32,
            generator=self._generate_waveform
        )
        if not res:
            return Result.error("WaveformDeviceST: failed to create OnDemandAudioRingBuffer")

        self._ring_buffer = res.unwrapped

        res = DynamicAudioBufferMediator.create(self._ring_buffer)
        if not res:
            return Result.error("WaveformDeviceST: failed to create DynamicAudioBufferMediator")

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
            return Result.error("WaveformDeviceST: buffer mediator not initialized")

        return self._buffer_mediator.open()

    def start(self):
        """Start waveform generation (virtual clock)."""
        if self._ring_buffer:
            self._ring_buffer.start()

    def stop(self):
        """Stop waveform generation."""
        if self._ring_buffer:
            self._ring_buffer.stop()

    def is_alive(self) -> bool:
        """Check if device is running."""
        return self._ring_buffer is not None and self._ring_buffer._running

    def dispose(self) -> Result[None]:
        """Stop generation and clean up."""
        self.stop()
        return Ok(None)

    def _generate_waveform(self) -> np.ndarray:
        """Generate waveform samples and return the buffer."""
        phase_increment = 2.0 * np.pi * self._frequency / self._sample_rate

        np.multiply(np.arange(self._period_size, dtype=np.float32), phase_increment, out=self._sample_buffer)
        np.add(self._sample_buffer, self._phase, out=self._sample_buffer)

        self._phase = (self._phase + self._period_size * phase_increment) % (2.0 * np.pi)

        if self._waveform_type == "sine":
            np.sin(self._sample_buffer, out=self._sample_buffer)
        elif self._waveform_type == "square":
            np.sin(self._sample_buffer, out=self._sample_buffer)
            np.sign(self._sample_buffer, out=self._sample_buffer)
        elif self._waveform_type == "triangle":
            np.divide(self._sample_buffer, 2.0 * np.pi, out=self._sample_buffer)
            np.remainder(self._sample_buffer, 1.0, out=self._sample_buffer)
            np.multiply(self._sample_buffer, 2.0, out=self._sample_buffer)
            np.subtract(self._sample_buffer, 1.0, out=self._sample_buffer)
            np.abs(self._sample_buffer, out=self._sample_buffer)
            np.multiply(self._sample_buffer, 2.0, out=self._sample_buffer)
            np.subtract(self._sample_buffer, 1.0, out=self._sample_buffer)

        return self._sample_buffer

    def get_children_names(self, path: DataPath) -> Result[List[str]]:
        """Get children for browsing."""
        if len(path) == 0 or str(path) == "/":
            return Ok([])
        return Ok([])

    def get_metadata(self, path: DataPath) -> Result[Dict]:
        """Get metadata for this device."""
        if len(path) == 0 or str(path) == "/":
            meta = {
                "uid": self.uid,
                "label": f"{self._waveform_type.capitalize()} ({self._frequency}Hz)",
                "type": "waveform-device-st",
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
            if self._buffer_mediator:
                meta["instance"] = self._buffer_mediator
            return Ok(meta)

        return Result.error(f"WaveformDeviceST: unknown path {path}")

    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        """Get metadata keys using existing get_metadata."""
        res = self.get_metadata(path)
        if not res:
            return Result.error(f"WaveformDeviceST: failed to get metadata for {path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            return Ok(list(metadata.keys()))
        return Result.error(f"WaveformDeviceST: metadata is not a dict at {path}")

    def get(self, path: DataPath) -> Result:
        """Get metadata value - last component of path is the key."""
        node_path = path.dirname()
        key = path.filename()

        res = self.get_metadata(node_path)
        if not res:
            return Result.error(f"WaveformDeviceST: failed to get metadata for {node_path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            if key in metadata:
                return Ok(metadata[key])
            return Result.error(f"WaveformDeviceST: key '{key}' not found in metadata at {node_path}")
        return Result.error(f"WaveformDeviceST: metadata is not a dict at {node_path}")

    def set(self, path: DataPath, value) -> Result[None]:
        """Set not implemented."""
        return Result.error("WaveformDeviceST: set: not implemented")

    def add_child(self, path: DataPath, value) -> Result[None]:
        """Add child not implemented."""
        return Result.error("WaveformDeviceST: add_child: not implemented")

    def as_tree(self, data_path: DataPath = None, depth: int = 0) -> Result[Union[dict]]:
        pass


@device_manager
class WaveformManagerST(AudioDeviceManager):
    """Single-threaded manager for waveform generators (Pyodide/WebAssembly)."""

    WAVEFORMS = ["sine", "square", "triangle"]

    def __init__(self):
        super().__init__()
        self._waveform_devices = {}

    def init(self) -> Result[None]:
        """Initialize waveform manager."""
        return Ok(None)

    def configure(self, config: dict) -> Result[None]:
        """Configure waveform manager."""
        return Ok(None)

    def dispose(self) -> Result[None]:
        """Clean up all waveform devices."""
        for path, device in self._waveform_devices.items():
            device.stop()
        self._waveform_devices.clear()
        return Ok(None)

    def get_children_names(self, path: DataPath) -> Result[List[str]]:
        """Get children for browsing."""
        if len(path) == 0 or str(path) == "/":
            return Ok(["available", "opened"])

        if len(path) > 0 and path[0] in ["available", "opened"]:
            branch = path[0]
            subpath = path[1:]

            if branch == "available":
                return self._get_children_names_available(subpath)
            else:
                return self._get_children_names_opened(subpath)

        return Result.error(f"WaveformManagerST: unknown path {path}")

    def _get_children_names_available(self, path: DataPath) -> Result[List[str]]:
        """Get children for /available branch."""
        if len(path) == 0 or str(path) == "/":
            return Ok(self.WAVEFORMS)

        if len(path) == 1 and path[0] in self.WAVEFORMS:
            return Ok(["0"])

        return Ok([])

    def _get_children_names_opened(self, path: DataPath) -> Result[List[str]]:
        """Get children for /opened branch."""
        if len(path) == 0 or str(path) == "/":
            if len(self._waveform_devices) > 0:
                return Ok([path[0] for path in self._waveform_devices.keys()])
            return Ok([])

        if len(path) >= 1 and path[0] in self.WAVEFORMS:
            device_path = DataPath("/" + path[0])
            device = self._waveform_devices.get(device_path)
            if not device:
                return Result.error(f"WaveformManagerST: device at {device_path} is not opened")

            subpath = DataPath(path.as_list[1:]) if len(path) > 1 else DataPath("/")
            return device.get_children_names(subpath)

        return Ok([])

    def get_metadata(self, path: DataPath) -> Result[Dict]:
        """Get metadata for a path."""
        if len(path) == 0 or str(path) == "/":
            return Ok({
                "uid": self.uid,
                "name": "waveform-st",
                "label": "Waveform Generator (Single-Threaded)",
                "type": "waveform-manager-st",
                "category": "audio-device-manager",
                "description": "Generates standard waveforms (sine, square, triangle) - single-threaded for Pyodide"
            })

        if len(path) == 1 and path[0] in ["available", "opened"]:
            return Ok({
                "name": path[0],
                "label": path[0].capitalize(),
                "type": "folder",
                "category": "folder"
            })

        if len(path) > 0 and path[0] in ["available", "opened"]:
            branch = path[0]
            subpath = path[1:]

            if branch == "available":
                return self._get_metadata_available(subpath)
            else:
                return self._get_metadata_opened(subpath)

        return Result.error(f"WaveformManagerST: unknown path {path}")

    def _get_metadata_available(self, path: DataPath) -> Result[Dict]:
        """Get metadata for /available branch."""
        if len(path) == 1 and path[0] in self.WAVEFORMS:
            waveform_type = path[0]
            return Ok({
                "name": waveform_type,
                "label": f"{waveform_type.capitalize()} Wave",
                "type": "waveform-device-st",
                "category": "audio-device",
                "description": f"{waveform_type.capitalize()} waveform generator (single-threaded)",
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

        return Result.error(f"WaveformManagerST: unknown available path {path}")

    def _get_metadata_opened(self, path: DataPath) -> Result[Dict]:
        """Get metadata for /opened branch."""
        if len(path) == 1 and path[0] in self.WAVEFORMS:
            device_path = DataPath("/" + path[0])
            device = self._waveform_devices.get(device_path)
            if not device:
                return Result.error(f"WaveformManagerST: device at {device_path} is not opened")

            return device.get_metadata(DataPath("/"))

        if len(path) >= 2 and path[0] in self.WAVEFORMS:
            device_path = DataPath("/" + path[0])
            device = self._waveform_devices.get(device_path)
            if not device:
                return Result.error(f"WaveformManagerST: device at {device_path} is not opened")

            subpath = DataPath(path.as_list[1:])
            return device.get_metadata(subpath)

        return Result.error(f"WaveformManagerST: unknown opened path {path}")

    def open(self, path: DataPath, config: dict) -> Result:
        """Open a waveform channel."""
        if len(path) != 3 or path[0] != "available" or path[1] not in self.WAVEFORMS or path[2] != "0":
            return Result.error(f"WaveformManagerST: invalid channel path {path}, expected /available/waveform_type/0")

        waveform_type = path[1]
        device_path = DataPath("/" + waveform_type)

        if device_path not in self._waveform_devices:
            frequency = config.get("frequency", 440.0)
            sample_rate = config.get("sample_rate", 48000)
            period_size = config.get("period_size", 1024)

            res = WaveformDeviceST.create(
                waveform_type=waveform_type,
                sample_rate=sample_rate,
                frequency=frequency,
                period_size=period_size
            )
            if not res:
                return Result.error(f"WaveformManagerST: failed to create {waveform_type} device", res)

            device = res.unwrapped
            device.start()
            self._waveform_devices[device_path] = device

        device = self._waveform_devices[device_path]
        return device.open(DataPath("/"), config)

    def close(self, path: DataPath) -> Result[None]:
        """Close a waveform generator."""
        if path not in self._waveform_devices:
            return Result.error(f"WaveformManagerST: device at {path} not opened")

        device = self._waveform_devices[path]
        device.stop()
        del self._waveform_devices[path]

        return Ok(None)

    def get_metadata_keys(self, path: DataPath) -> Result[list]:
        """Get metadata keys using existing get_metadata."""
        res = self.get_metadata(path)
        if not res:
            return Result.error(f"WaveformManagerST: failed to get metadata for {path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            return Ok(list(metadata.keys()))
        return Result.error(f"WaveformManagerST: metadata is not a dict at {path}")

    def get(self, path: DataPath) -> Result[Any]:
        """Get metadata value - last component of path is the key."""
        node_path = path.dirname()
        key = path.filename()

        res = self.get_metadata(node_path)
        if not res:
            return Result.error(f"WaveformManagerST: failed to get metadata for {node_path}", res)
        metadata = res.unwrapped
        if isinstance(metadata, dict):
            if key in metadata:
                return Ok(metadata[key])
            return Result.error(f"WaveformManagerST: key '{key}' not found in metadata at {node_path}")
        return Result.error(f"WaveformManagerST: metadata is not a dict at {node_path}")

    def set(self, path: DataPath, value) -> Result[None]:
        """Set not implemented."""
        return Result.error("WaveformManagerST: set: not implemented")

    def add_child(self, path: DataPath, value) -> Result[None]:
        """Add child not implemented."""
        return Result.error("WaveformManagerST: add_child: not implemented")

    def as_tree(self, data_path: DataPath = None, depth: int = 0) -> Result[Union[dict]]:
        pass


def main():
    """Test the single-threaded waveform generator."""
    res = WaveformManagerST.create()
    if not res:
        print("error:", res)
        return

    manager = res.unwrapped

    # Open sine waveform
    res = manager.open(DataPath("/available/sine/0"), {"frequency": 440.0})
    if not res:
        print("error:", res)
        return

    mediated_buffer = res.unwrapped
    print(f"Opened mediated buffer: {mediated_buffer}")

    # Wait a bit and check data
    import time
    time.sleep(0.1)

    data = mediated_buffer.data
    print(f"Data length: {len(data) if data is not None else 0}")
    print(f"First 10 samples: {data[:10] if data is not None and len(data) >= 10 else data}")


if __name__ == "__main__":
    main()
