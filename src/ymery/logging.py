import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, List, Any, Dict

# Characters for UID generation (letters + digits)
_UID_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz"


def _hash_to_uid(h: int, length: int = 10) -> str:
    """Convert a hash to a short UID string (letters + digits)."""
    h = abs(h)
    base = len(_UID_CHARS)
    result = []
    for _ in range(length):
        result.append(_UID_CHARS[h % base])
        h //= base
    return ''.join(result)


def _compute_msg_hash(record: logging.LogRecord) -> int:
    """Compute hash for deduplication based on message content."""
    msg = record.msg
    if hasattr(msg, '__hash__') and callable(msg.__hash__):
        try:
            msg_hash = hash(msg)
        except TypeError:
            msg_hash = hash(str(msg))
    else:
        msg_hash = hash(str(msg))
    return hash((record.levelno, record.name, msg_hash))


@dataclass
class _DedupEntry:
    """Tracks a deduplicated message."""
    uid: str
    count: int = 1
    first_time: float = field(default_factory=time.time)
    last_summary_time: float = field(default_factory=time.time)
    level: int = logging.ERROR
    name: str = "root"


class DedupFilter(logging.Filter):
    """
    Filter that deduplicates log messages.

    - First occurrence: adds UID, allows through
    - Repeated: suppresses, but emits summary every dedup_window seconds
    """

    def __init__(self, dedup_window: float = 1.0):
        super().__init__()
        self.dedup_window = dedup_window
        self._cache: Dict[int, _DedupEntry] = {}

    def filter(self, record: logging.LogRecord) -> bool:
        msg_hash = _compute_msg_hash(record)
        current_time = time.time()

        if msg_hash in self._cache:
            entry = self._cache[msg_hash]
            entry.count += 1

            # Check if it's time to emit summary
            if current_time - entry.last_summary_time >= self.dedup_window:
                elapsed = int(current_time - entry.first_time)
                # Modify record to be a summary
                record.msg = f"error '{entry.uid}' repeated {entry.count} times the last {elapsed} seconds"
                record.args = ()
                record.uid = entry.uid
                entry.last_summary_time = current_time
                return True

            # Suppress duplicate
            return False
        else:
            # New unique message
            uid = _hash_to_uid(msg_hash)
            self._cache[msg_hash] = _DedupEntry(
                uid=uid,
                count=1,
                first_time=current_time,
                last_summary_time=current_time,
                level=record.levelno,
                name=record.name
            )
            record.uid = uid
            return True


@dataclass
class LogEntry:
    """A log entry stored in the ring buffer."""
    record: logging.LogRecord
    timestamp: float = field(default_factory=time.time)

    @property
    def uid(self) -> str:
        return getattr(self.record, 'uid', '')

    @property
    def msg(self) -> Any:
        return self.record.msg

    @property
    def level(self) -> int:
        return self.record.levelno

    @property
    def level_name(self) -> str:
        return self.record.levelname

    @property
    def name(self) -> str:
        return self.record.name


class RingBufferHandler(logging.Handler):
    """Simple ring buffer handler - just stores records."""

    def __init__(self, capacity: int = 100):
        super().__init__()
        self.buffer: deque[LogEntry] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.buffer.append(LogEntry(record=record, timestamp=time.time()))
        except Exception:
            self.handleError(record)

    def get_entries(self) -> List[LogEntry]:
        return list(self.buffer)

    def clear(self) -> None:
        self.buffer.clear()


# Global instances
_ring_buffer_handler: Optional[RingBufferHandler] = None
_dedup_filter: Optional[DedupFilter] = None


def get_ring_buffer() -> Optional[RingBufferHandler]:
    return _ring_buffer_handler


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    ring_buffer_capacity: int = 100,
    dedup_window: float = 1.0
) -> RingBufferHandler:
    """
    Configure logging with deduplication, optional file output, and ring buffer.
    """
    global _ring_buffer_handler, _dedup_filter

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.filters.clear()

    # Single dedup filter for all handlers
    _dedup_filter = DedupFilter(dedup_window=dedup_window)
    root_logger.addFilter(_dedup_filter)

    # Formatter with UID
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(uid)s: %(message)s',
        datefmt='%H:%M:%S'
    )

    # Stream or file handler
    if log_file is None:
        handler = logging.StreamHandler()
    else:
        handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    handler.setLevel(level)
    root_logger.addHandler(handler)

    # Ring buffer handler
    _ring_buffer_handler = RingBufferHandler(capacity=ring_buffer_capacity)
    _ring_buffer_handler.setLevel(level)
    root_logger.addHandler(_ring_buffer_handler)

    return _ring_buffer_handler


def log(*args):
    """Simple log function for backward compatibility."""
    logging.info(' '.join(str(arg) for arg in args))
