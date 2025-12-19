"""
this module implements different buffer abstractions used in the WaeW application
for modelling different buffer usage scenarios both for static and dynamic buffers
It considers thus following aspects
* static vs dynamic
* subbufer (slice) vs original buffer

In order to avoid unnecessary locking of the buffers the implementation
is rather tuned to represent slices as copies, though they are in fact slices
"""

from abc import ABC, abstractmethod
import numpy as np
import threading
from typing import Optional

from ymery.types import Object
from ymery.backend.types import Buffer
from ymery.result import Result, Ok

class AudioBufferRange:
    def __init__(self, start: int, length: int):
        pass

class AudioBuffer(Buffer):
    """
    Abstract base class used for buffer manipulation
    A buffer stores data only for one channel
    Providers need to provide separate buffer for each channel
    """

    @abstractmethod
    def init(self):
        """
        while __init__ should be called with dependencies that are consumed by an instance
        any real initialization should happen in the init, especially if exception is thrown
        """
        pass

    @abstractmethod
    def lock(self):
        """
        generic method that marks the buffer being used
        this may have no implementation, however for dynamic buffers 
        this should implement the thread safety locking
        """
        pass

    @abstractmethod
    def unlock(self):
        """
        generic method that marks the buffer being used
        this may have no implementation, however for dynamic buffers
        this should implement the thread safety locking
        """
        pass



    @property
    @abstractmethod
    def data(self):
        """
        access to internal data
        should return a numpy view or numpy buffer ready to be consumed by visuals (plots, etc)
        """
        pass


class DynamicAudioBuffer(AudioBuffer):
    """
    Abstraction to model dynamic buffers used for instance to read 
    chunks from a device
    """
    pass


class DynamicAudioRingBuffer(DynamicAudioBuffer):
    """
    Double-depth ring buffer with per-channel storage.

    Physical buffer size: 2N (double-depth for continuous views)
    Logical buffer size: N (exposed to clients)
    Write pointer wraps at: N

    Features:
    - Per-channel separate numpy arrays (lazy allocation)
    - Active/frozen channel management
    - Thread-safe with single global lock
    - Continuous views without wrap-around
    """

    def __init__(self, sample_rate: int, initial_size: int = 0,
                 period_size: Optional[int] = None, format_type: type = np.float32):
        """Initialize dynamic ring buffer for ONE channel.

        Args:
            sample_rate: Sample rate in Hz
            initial_size: Initial logical buffer size in samples (0 for minimal)
            period_size: Period size for rounding (optional)
            format_type: Numpy data type for samples
        """
        self._sample_rate = sample_rate
        self._period_size = period_size or 1024
        self._format = format_type

        # Use minimal size if initial_size is 0
        if initial_size == 0:
            initial_size = self._period_size

        # Logical size (exposed to clients)
        self._buffer_size = self._round_to_period(initial_size)

        # Physical size (internal double-depth)
        self._physical_size = self._buffer_size * 2

        # Single channel buffer (one buffer = one channel)
        self._buffer = None  # Lazy allocation

        # Buffer state
        self._active = False  # Has mediated buffers attached
        self._frozen = False  # Allocated but not updating

        self._ptr = 0  # Write pointer (wraps at _buffer_size)
        self._has_wrapped = False  # Track if we've wrapped around at least once
        self._lock = threading.Lock()

    def _round_to_period(self, size: int) -> int:
        """Round size up to multiple of period size."""
        return ((size + self._period_size - 1) // self._period_size) * self._period_size

    def _allocate(self):
        """Allocate buffer (lazy allocation)."""
        if self._buffer is None:
            self._buffer = np.zeros(self._physical_size, dtype=self._format)

    def activate(self):
        """Activate buffer (first mediated buffer attached)."""
        if not self._active:
            self._allocate()
            self._active = True

    def deactivate(self):
        """Deactivate buffer (last mediated buffer detached)."""
        if self._active:
            # Deallocate unless frozen
            if not self._frozen:
                self._buffer = None
            self._active = False

    def freeze(self):
        """Freeze buffer (keep buffer, stop updates)."""
        self._frozen = True

    def unfreeze(self):
        """Unfreeze buffer (resume updates)."""
        self._frozen = False

    def lock(self):
        """Acquire lock for thread-safe access."""
        self._lock.acquire()

    def unlock(self):
        """Release lock."""
        self._lock.release()

    def try_lock(self) -> bool:
        """Try to acquire lock without blocking.

        Returns:
            True if lock acquired, False otherwise
        """
        return self._lock.acquire(blocking=False)


    def set_range(self, start: int, length: int):
        """Resize logical buffer length (blocking lock).

        Args:
            start: Must be 0 (no sliding window for dynamic buffers)
            length: New logical buffer length in samples

        Raises:
            ValueError: If start is nonzero
        """
        if start != 0:
            raise ValueError(f"DynamicRingBuffer.set_range() requires start=0, got {start}")

        new_length = self._round_to_period(length)

        # Don't resize if size hasn't changed
        if new_length == self._buffer_size:
            return

        self.lock()
        try:
            old_length = self._buffer_size
            old_physical = self._physical_size
            old_ptr = self._ptr

            # Update sizes
            self._buffer_size = new_length
            self._physical_size = new_length * 2

            # Resize buffer if allocated
            if self._buffer is not None:
                # Get the useful data from old buffer before resizing
                old_useful_data = self.data  # This handles the double-depth logic correctly

                # Allocate new double-depth buffer
                new_buffer = np.zeros(self._physical_size, dtype=self._format)

                # Copy useful data to new buffer (up to new_length samples)
                if old_useful_data is not None and len(old_useful_data) > 0:
                    data_to_copy = min(len(old_useful_data), new_length)
                    new_buffer[:data_to_copy] = old_useful_data[-data_to_copy:]

                self._buffer = new_buffer

                # Reset pointer to amount of data copied
                self._ptr = min(len(old_useful_data) if old_useful_data is not None else 0, new_length)
            else:
                # Buffer not yet allocated, just reset pointer
                self._ptr = 0

            # Reset wrap flag (new cycle starts)
            self._has_wrapped = False
        finally:
            self.unlock()


    def set_sample_rate(self, sample_rate: int):
        """Set sample rate."""
        self._sample_rate = sample_rate

    def set_format(self, format_type: type):
        """Set data format type."""
        self._format = format_type

    def write(self, data: np.ndarray):
        """Write data to ring buffer (blocking lock from provider thread).

        Double-depth ring buffer mechanics:
        - Physical size: 2N, logical size: N
        - ptr goes from 0 to 2N
        - When ptr reaches N: copy second half [N:2N] → first half [0:N], continue writing from N
        - When ptr reaches 2N: copy second half [N:2N] → first half [0:N], wrap ptr to N

        Args:
            data: Numpy array of samples (1D array for single channel)
        """
        self.lock()
        try:
            n = len(data)  # Number of samples

            # Write if active and not frozen
            if self._active and not self._frozen:
                if self._buffer is None:
                    self._allocate()

                # Check if we need to wrap BEFORE writing
                if self._ptr >= self._physical_size:
                    # Reached end of physical buffer (2N)
                    # Copy second half to first half
                    self._buffer[:self._buffer_size] = \
                        self._buffer[self._buffer_size:self._physical_size]
                    # Wrap pointer back to N (middle of physical buffer)
                    self._ptr = self._buffer_size

                # Check if we crossed the logical boundary (N)
                if self._ptr >= self._buffer_size and not self._has_wrapped:
                    # First time crossing N
                    # Copy second half to first half
                    self._buffer[:self._buffer_size] = \
                        self._buffer[self._buffer_size:self._physical_size]
                    self._has_wrapped = True

                # Write at current position
                self._buffer[self._ptr:self._ptr+n] = data

            # Advance pointer
            self._ptr += n
        finally:
            self.unlock()


    @property
    def data(self) -> Optional[np.ndarray]:
        """Get useful data snapshot (most recent N samples ending at ptr).

        Returns the "useful" part of the buffer - the most recent samples
        ending at the current write position.

        With double-depth ring buffer:
        - ptr ranges from 0 to 2N
        - Before first wrap (ptr < N): return [0:ptr]
        - After wrap (ptr >= N): return most recent N samples = [ptr-N:ptr]

        WARNING: Caller must lock/unlock before/after accessing this property!

        Returns:
            Numpy view of useful data (most recent samples ending at ptr),
            or None if not allocated
        """
        if self._buffer is None:
            return None

        # Before reaching N, return all samples written so far
        if self._ptr < self._buffer_size:
            return self._buffer[0:self._ptr]

        # After reaching N, always return the most recent N samples
        # ptr ranges from N to 2N, so [ptr-N:ptr] gives us the last N samples
        start = self._ptr - self._buffer_size
        return self._buffer[start:self._ptr]

    def init(self) -> Result[None]:
        """Initialize buffer (already done in __init__)."""
        return Ok(None)

    def close(self):
        """Close buffer and free resources."""
        self.lock()
        try:
            self._buffer = None
            self._active = False
        finally:
            self.unlock()

    def dispose(self):
        self.close()


class MediatedAudioBuffer(AudioBuffer):
    """
    View into source buffer - holds only metadata, no data copy.

    One mediated buffer views one channel from the source.
    Consumer slices the data property to get desired window.
    """

    def __init__(self, mediator: 'BufferMediator', start: Optional[int] = 0, length: Optional[int] = None):
        """Initialize mediated buffer.

        Args:
            mediator: Parent BufferMediator instance
            start: start position for slicing
            length: lengh for slicing
        """
        super().__init__()
        self._mediator = mediator
        self._start = 0  # Start position for slicing
        self._length = 65536 if length is None else length # Default length


    def set_range(self, start: int, length: int):
        """Set view range (atomic update).

        Args:
            start: Start position for slicing
            length: Number of samples
        """
        self._start = start
        self._length = length
        # Notify mediator to resize source buffer if needed
        self._mediator._resize_source_if_needed()

    @property
    def data(self) -> np.ndarray:
        """Get sliced view of the channel data.

        Returns data[start:start+length] from the source buffer.
        For dynamic buffers, clamps to available data.

        Returns:
            Numpy array slice or empty array
        """
        source_data = self._mediator.data
        if source_data is None:
            return np.array([])

        # Clamp slice to available data
        # For dynamic buffers, source_data.length may be less than requested
        available = len(source_data)
        start = min(self._start, available)
        end = min(self._start + self._length, available)

        return source_data[start:end]

    def close(self):
        """Close this mediated buffer and notify mediator."""
        self._mediator._remove_mediated_buffer(self._mediated_id)

    def init(self) -> Result[None]:
        """Initialize (already done in __init__)."""
        return Ok(None)

    # Buffer ABC methods (delegate to mediator/source)
    def try_lock(self) -> bool:
        """Try to lock source buffer (non-blocking).

        Returns:
            True if lock acquired, False if busy
        """
        return self._mediator.try_lock()

    def lock(self):
        """Lock source buffer via mediator."""
        self._mediator.lock()

    def unlock(self):
        """Unlock source buffer via mediator."""
        self._mediator.unlock()

    def set_sample_rate(self):
        """Not applicable for mediated buffer."""
        pass

    def set_format(self):
        """Not applicable for mediated buffer."""
        pass

    def set_start(self, start: int):
        """
        set's the buffer start.
        start is relative to the "parents" buffer if any
        """
        self._start = start

    def set_length(self, length: int):
        """
        set's the buffer length 
        start is relative to the "parents" buffer if any
        """
        self._length = length

    def dispose(self) -> Result[None]:
        return Ok(None)


class AudioBufferMediator(Object):
    """
    Mediates access to source buffer for multiple consumers.

    Responsibilities:
    - Resize source buffer based on max consumer length
    - Track channel activation/deactivation
    - Coordinate locking between consumers and source
    """

    def __init__(self, backend: Buffer):
        """Initialize mediator.

        Args:
            source_buffer: The source Buffer to mediate
        """
        self._backend = backend
        self._mediated_buffers = {}

    @property
    def backend(self):
        return self._backend

    @abstractmethod
    def open(self) -> MediatedAudioBuffer:
        """open the mediated buffer

        Returns:
            MediatedBuffer instance
        """
        pass


    def _remove_mediated_buffer(self, mediated_id: str) -> Result[None]:
        """Remove a mediated buffer and update source.

        Args:
            mediated_id: ID of mediated buffer to remove
        """
        if mediated_id not in self._mediated_buffers:
            return Result.error(f"{mediated_id} not found in buffers map")

        del self._mediated_buffers[mediated_id]

        self._resize_source_if_needed()

    def _resize_source_if_needed(self):
        """Resize source buffer based on largest consumer request."""
        if not self._mediated_buffers:
            return

        # Find the maximum end position needed by all consumers
        max_end = max(buf._start + buf._length for buf in self._mediated_buffers.values())

        # Resize source buffer to accommodate all consumers
        self._backend.set_range(start=0, length=max_end)

    # Buffer ABC methods (delegate to source)
    def lock(self):
        """Lock source buffer."""
        self._backend.lock()

    def unlock(self):
        """Unlock source buffer."""
        self._backend.unlock()

    def try_lock(self) -> bool:
        """Try to lock source buffer (non-blocking)."""
        return self._backend.try_lock()


    @property
    def data(self) -> np.ndarray:
        """Get full buffer data from source.

        Returns:
            Numpy view of source buffer data
        """
        return self._backend.data


class DynamicAudioBufferMediator(AudioBufferMediator):
    """Mediator for dynamic buffers (e.g., ring buffers from ALSA/JACK)."""

    def __init__(self, source_buffer: DynamicAudioBuffer):
        """Initialize dynamic buffer mediator.

        Args:
            source_buffer: DynamicBuffer (e.g., DynamicRingBuffer) to mediate
        """
        super().__init__(source_buffer)

    def open(self, start: Optional[int] = 0, length: Optional[int] = None) -> Result['MediatedAudioBuffer']:
        """Create a new mediated dynamic buffer.

        Args:

        Returns:
            MediatedAudioBuffer instance
        """

        res = MediatedAudioBuffer.create(self, start, length)
        if not res:
            Result.error(f"DynamicAudioBufferMediator: open: failed to create MediatedAudioBuffer", res)
        mediated_buffer = res.unwrapped
        self._mediated_buffers[mediated_buffer.uid] = mediated_buffer

        # Activate source buffer on first mediated buffer
        if not self._mediated_buffers or len(self._mediated_buffers) == 1:
            if hasattr(self._backend, 'activate'):
                self._backend.activate()

        # Resize source buffer to accommodate new consumer
        self._resize_source_if_needed()

        return Ok(mediated_buffer)

    def init(self) -> Result[None]:
        return Ok(None)

    def dispose(self) -> Result[None]:
        return Ok(None)



class StaticAudioBuffer(AudioBuffer):
    """
    Abstraction to model static buffers, for instance the in memory
    representation of a file.
    """
    pass


class FileAudioBuffer(StaticAudioBuffer):
    """Single-channel file buffer.

    One buffer = one channel.
    Providers create separate FileBuffer instance for each channel.
    """

    def __init__(self, file_path: str, data: np.ndarray, sample_rate: int):
        """Initialize file buffer for ONE channel.

        Args:
            file_path: Path to the audio file
            data: Numpy array of samples (1D array for single channel)
            sample_rate: Sample rate in Hz
        """
        self._file_path = file_path
        self._sample_rate = sample_rate
        self._num_samples = len(data)

        # Single channel buffer
        self._buffer = data.copy()

        # Active by default
        self._active = True

    def activate(self):
        """Activate buffer for lazy loading."""
        if not self._active:
            # TODO: Load data from file if needed
            self._active = True

    def deactivate(self):
        """Deactivate buffer to free memory."""
        if self._active:
            # TODO: Optionally deallocate data
            self._active = False

    def lock(self):
        """No-op for static buffers - immutable after load."""
        pass

    def unlock(self):
        """No-op for static buffers."""
        pass

    def try_lock(self) -> bool:
        """Try to acquire lock (always succeeds for static buffers).

        Returns:
            Always True (static buffers don't need locking)
        """
        return True

    def set_range(self, start: int, length: int):
        """No-op for file buffers - size is fixed."""
        pass

    def set_sample_rate(self, sample_rate: int):
        """Set sample rate."""
        self._sample_rate = sample_rate

    def set_format(self):
        """Not applicable - determined by loaded data."""
        pass

    @property
    def data(self) -> Optional[np.ndarray]:
        """Get full buffer data.

        Returns:
            Numpy view of entire buffer or None if not active
        """
        if not self._active:
            return None
        return self._buffer

    def init(self):
        """Initialize (already done in __init__)."""
        pass

    def close(self):
        """Close buffer and free resources."""
        self._buffer = None
        self._active = False


class StaticAudioBufferMediator(AudioBufferMediator):
    """Mediator for static buffers (e.g., loaded files)."""

    def __init__(self, source_buffer: StaticAudioBuffer):
        """Initialize static buffer mediator.

        Args:
            source_buffer: StaticBuffer (e.g., FileBuffer) to mediate
        """
        super().__init__(source_buffer)

    def open(self, start: Optional[int] = 0, length: Optional[int] = None) -> Result['MediatedStaticBuffer']:
        """Create a new mediated static buffer.

        Returns:
            MediatedStaticBuffer instance
        """

        res = MediatedAudioBuffer.create(self, start, length)
        if not res:
            return Result.error("StaticAudioBufferMediator: open: could not create MediatedStaticAudioBuffer", res)
        mediated_buffer = res.unwrapped
        self._mediated_buffers[mediated_buffer.uid] = mediated_buffer

        return Ok(mediated_buffer)
    
    def dispose(self):
        pass

    def init(self) -> Result[None]:
        return Ok(None)


