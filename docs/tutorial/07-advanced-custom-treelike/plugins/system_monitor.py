"""
System Monitor - A custom TreeLike implementation
that provides simulated system metrics.

This is a simplified example for the tutorial.
In a real application, you would use libraries like psutil
to get actual system data.
"""

from typing import Dict, Any, Optional
import time
import random
from ymery.backend.tree_like import TreeLike
from ymery.result import Result, Ok
from ymery.decorators import tree_like


@tree_like
class SystemMonitor(TreeLike):
    """
    Provides simulated system metrics as a tree structure.

    Usage in YAML:
        data:
          system:
            type: system-monitor

    Tree structure:
        system/
        ├── cpu/
        │   ├── usage (metadata)
        │   └── cores (metadata)
        ├── memory/
        │   ├── used (metadata)
        │   ├── total (metadata)
        │   └── percent (metadata)
        └── disk/
            ├── used (metadata)
            ├── total (metadata)
            └── percent (metadata)
    """

    def __init__(self, node_type: Optional[str] = None):
        """
        Initialize the system monitor.

        Args:
            node_type: None for root, or "cpu", "memory", "disk" for subsystems
        """
        self._node_type = node_type
        self._start_time = time.time()

    def _get_simulated_value(self, base: float, variance: float = 10) -> float:
        """Generate a simulated value that varies slightly over time"""
        # Add some randomness based on time for "live" feel
        offset = random.uniform(-variance, variance)
        return max(0, min(100, base + offset))

    def get_metadata(self, key: str) -> Result[Any]:
        """Get metadata for the current node"""

        if self._node_type is None:
            # Root node metadata
            if key == "label":
                return Ok("System Monitor")
            return Result.error(f"Unknown root metadata: {key}")

        elif self._node_type == "cpu":
            if key == "label":
                return Ok("CPU")
            elif key == "usage":
                return Ok(f"{self._get_simulated_value(45):.1f}%")
            elif key == "cores":
                return Ok("8")
            elif key == "frequency":
                return Ok("3.2 GHz")

        elif self._node_type == "memory":
            if key == "label":
                return Ok("Memory")
            elif key == "used":
                return Ok("8.2 GB")
            elif key == "total":
                return Ok("16.0 GB")
            elif key == "percent":
                return Ok(f"{self._get_simulated_value(51):.1f}%")

        elif self._node_type == "disk":
            if key == "label":
                return Ok("Disk")
            elif key == "used":
                return Ok("256 GB")
            elif key == "total":
                return Ok("512 GB")
            elif key == "percent":
                return Ok("50%")

        elif self._node_type == "network":
            if key == "label":
                return Ok("Network")
            elif key == "upload":
                return Ok(f"{self._get_simulated_value(1.5, 1):.2f} MB/s")
            elif key == "download":
                return Ok(f"{self._get_simulated_value(5.0, 2):.2f} MB/s")
            elif key == "status":
                return Ok("Connected")

        return Result.error(f"Unknown metadata key: {key}")

    def set_metadata(self, key: str, value: Any) -> Result[None]:
        """System monitor is read-only"""
        return Result.error("System monitor is read-only")

    def get_child(self, name: str) -> Result['TreeLike']:
        """Get a child subsystem by name"""
        if self._node_type is None:
            # Root can access subsystems
            if name in ["cpu", "memory", "disk", "network"]:
                return Ok(SystemMonitor(name))
        return Result.error(f"Child '{name}' not found")

    def get_children(self) -> Result[Dict[str, 'TreeLike']]:
        """Get all children of this node"""
        if self._node_type is None:
            # Root returns all subsystems
            return Ok({
                "cpu": SystemMonitor("cpu"),
                "memory": SystemMonitor("memory"),
                "disk": SystemMonitor("disk"),
                "network": SystemMonitor("network"),
            })
        # Subsystem nodes have no children
        return Ok({})

    def add_child(self, name: str, metadata: Dict[str, Any]) -> Result['TreeLike']:
        """System monitor is read-only"""
        return Result.error("System monitor is read-only")
