"""Filesystem DeviceManager - Browse and open files from filesystem"""
try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    sf = None
    SOUNDFILE_AVAILABLE = False
import os
from pathlib import Path
from functools import lru_cache

from imery.backend.types import AudioDeviceManager, TreeLikeCache
from imery.types import DataPath
from imery.decorators import device_manager

from imery.result import Result, Ok

from typing import Optional, Dict, Union

# Import SoundfileDevice from soundfile plugin (hardcoded for now)
from imery.plugins.soundfile.main import SoundfileDevice


@lru_cache(maxsize=1000)
def _get_soundfile_info(file_path: str):
    """Get SoundFile info with caching (maxsize=1000).

    Args:
        file_path: Path to audio file

    Returns:
        Tuple of (channels, samplerate, frames, format, subtype, endian) or None if not a valid audio file
    """
    if not SOUNDFILE_AVAILABLE:
        return None
    try:
        with sf.SoundFile(file_path, mode='r') as audio_file:
            return (
                audio_file.channels,
                audio_file.samplerate,
                len(audio_file),
                audio_file.format,
                audio_file.subtype,
                audio_file.endian
            )
    except Exception:
        return None


@device_manager
class FilesystemManager(TreeLikeCache, AudioDeviceManager):
    # Virtual shortcuts mapping for /available branch
    _VIRTUAL_SHORTCUTS = {
        "/fs-root": "/",
        "/home": str(Path.home())
    }

    def __init__(self):
        TreeLikeCache.__init__(self)
        AudioDeviceManager.__init__(self)
        self._soundfile_devices = {}  # Track opened SoundFileDevice instances by ID
        self._next_device_id = 0

    def init(self) -> Result[None]:
        """Initialize the filesystem manager."""
        return Ok(None)

    def dispose(self) -> Result[None]:
        """Clean up resources."""
        # Dispose all opened devices
        for device_id, device in self._soundfile_devices.items():
            # SoundfileProvider doesn't need explicit cleanup, but we could add dispose() if needed
            pass
        self._soundfile_devices.clear()
        return Ok(None)

    def _parse_mounts(self):
        """Parse /proc/self/mounts to get mounted filesystems.

        Returns:
            List of mount point paths
        """
        mounts = {}
        try:
            with open('/proc/self/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 3:
                        continue

                    device = parts[0]
                    mountpoint = parts[1]
                    fstype = parts[2]

                    # Filter out virtual/system filesystems
                    if fstype in ['proc', 'sysfs', 'devpts', 'devtmpfs', 'tmpfs',
                                  'cgroup', 'cgroup2', 'pstore', 'bpf', 'configfs',
                                  'debugfs', 'tracefs', 'securityfs', 'fusectl',
                                  'fuse.gvfsd-fuse', 'fuse.portal']:
                        continue

                    # Filter out special device names
                    if device.startswith(('proc', 'sysfs', 'devpts', 'tmpfs',
                                         'cgroup', 'pstore', 'bpf', 'configfs',
                                         'debugfs', 'tracefs', 'securityfs', 'fusectl')):
                        continue

                    # Add valid mount points
                    if mountpoint and mountpoint != '/':
                        mounts[mountpoint] = {
                            "device": device,
                            "fstype": fstype
                        }
        except (FileNotFoundError, PermissionError) as e:
            return Result.error("could not read /proc/self/mounts", e)

        return Ok(mounts)

    def _map_virtual_to_real(self, path: DataPath) -> str:
        """Map virtual shortcut path to real filesystem path.

        Args:
            path: Internal-path (could be virtual or real)

        Returns:
            Real filesystem path
        """
        # Convert to string for comparisons
        path_str = str(path)

        # Check if it's a virtual shortcut root
        if path_str in self._VIRTUAL_SHORTCUTS:
            return self._VIRTUAL_SHORTCUTS[path_str]

        # Check if path starts with a virtual shortcut
        for virtual, real in self._VIRTUAL_SHORTCUTS.items():
            if path_str.startswith(virtual):
                # Replace virtual prefix with real path
                suffix = path_str[len(virtual):]  # e.g., "/Documents"
                return real + suffix

        # Not a virtual path, return as-is (already a real path)
        return path_str

    def _map_real_to_virtual(self, real_path: str, parent_virtual: str) -> str:
        """Map real filesystem path back to virtual path under a parent shortcut.

        Args:
            real_path: Real filesystem path
            parent_virtual: Parent virtual shortcut (e.g., "/home")

        Returns:
            Virtual path
        """
        if parent_virtual not in self._VIRTUAL_SHORTCUTS:
            # Not under a virtual shortcut, return as-is
            return real_path

        real_parent = self._VIRTUAL_SHORTCUTS[parent_virtual]

        # Special case: when real_parent is "/", we need to keep the full path
        if real_parent == "/":
            return parent_virtual + real_path

        # Check if real_path is under real_parent
        if real_path.startswith(real_parent):
            # Replace real parent with virtual parent
            suffix = real_path[len(real_parent):]
            return parent_virtual + suffix

        # Not under this virtual parent, return as-is
        return real_path

    def get_children_names_uncached(self, path: DataPath):
        """Returns children for hierarchical browsing.

        Args:
            path: Internal-path (relative to plugin)

        Returns:
            List of internal-paths
        """
        # Root: "/" - return available and opened branches
        if len(path) == 0 or path == "/":
            return Ok(["available", "opened"])

        # Handle both /available and /opened branches
        if len(path) > 0 and path[0] in ["available", "opened"]:
            branch = path[0]
            subpath = path[1:]  # Strip branch prefix

            if branch == "opened":
                return self._get_opened_children(subpath)
            else:  # branch == "available"
                return self._get_available_children(subpath)

        return Ok([])

    def _get_opened_children(self, path: DataPath):
        """Get children for /opened branch - opened devices"""
        # Root: "/" -> return list of opened device IDs
        if len(path) == 0 or path == "/":
            return Ok([str(device_id) for device_id in self._soundfile_devices.keys()])

        # Device path: "/opened/0" -> delegate to device
        if len(path) >= 1:
            try:
                device_id = int(path[0])
                if device_id in self._soundfile_devices:
                    device = self._soundfile_devices[device_id]
                    subpath = path[1:]  # Strip device_id
                    return device.get_children_names(subpath)
            except ValueError:
                pass

        return Ok([])

    def _get_available_children(self, path: DataPath):
        """Get children for /available branch - filesystem browsing"""
        # Convert to string for comparisons
        path_str = str(path)

        # Root: "/" - return virtual shortcuts
        if path_str == "/" or len(path) == 0:
            return Ok(["fs-root", "home", "mounts", "bookmarks"])

        print(f"get_children_names_uncached 0: {path_str}")
        # /mounts - list mounted filesystems from /proc/self/mounts
        if path_str == "/mounts":
            res = self._parse_mounts()
            if not res:
                return Result.error("could not read mounts", res)
            # Return mount paths as absolute paths (starting with "/")
            # These will be appended via DataPath / operator which strips leading "/"
            mount_paths = list(res.unwrapped.keys())
            return Ok(mount_paths)

        print(f"get_children_names_uncached 1: {path_str}")

        # /bookmarks - placeholder
        if path_str == "/bookmarks":
            return Ok([])

        # Check if parent is under /mounts
        if path_str.startswith("/mounts/"):
            # Extract the real filesystem path
            # E.g., "/mounts/boot/efi" -> "/boot/efi"
            fs_path = path_str[len("/mounts"):]
        else:
            # Map virtual path to real filesystem path
            fs_path = self._map_virtual_to_real(path)

        if not os.path.exists(str(fs_path)):
            return Ok([])

        if not os.path.isdir(str(fs_path)):
            # Check if it's an audio file
            info = _get_soundfile_info(str(fs_path))
            if info:
                # Audio file - return channel indices as children
                channels = info[0]
                return Ok([str(i) for i in range(channels)])
            # Non-audio file - no children
            return Ok([])

        # Determine which virtual shortcut we're under (if any)
        parent_virtual = None
        for virtual in self._VIRTUAL_SHORTCUTS.keys():
            if path_str == virtual or path_str.startswith(virtual + "/"):
                parent_virtual = virtual
                break

        # Check if we're under /mounts
        if path_str.startswith("/mounts/"):
            parent_virtual = "/mounts"

        # List directory contents
        children = []
        try:
            for entry in sorted(os.listdir(str(fs_path))):
                entry_path = os.path.join(str(fs_path), entry)
                children.append(entry)
        except PermissionError:
            pass

        return Ok(children)


    def get_metadata_uncached(self, path: DataPath):
        """Returns metadata for a node.

        Args:
            path: Internal-path (relative to plugin)

        Returns:
            Metadata dictionary
        """
        # Root: "/"
        if len(path) == 0 or path == "/":
            return Ok({
                "uid": self.uid,
                "name": "filesystem",
                "label": "Filesystem",
                "type": "filesystem-manager",
                "category": "audio-device-manager",
                "description": "Browse and open audio files from filesystem"
            })

        # Handle both /available and /opened branches
        if len(path) > 0 and path[0] in ["available", "opened"]:
            branch = path[0]
            subpath = path[1:]

            if branch == "opened":
                return self._get_opened_metadata(subpath)
            else:  # branch == "available"
                return self._get_available_metadata(subpath)

        return Result.error(f"FilesystemManager: invalid path {path}")

    def _get_opened_metadata(self, path: DataPath):
        """Get metadata for /opened branch"""
        # Root: "/" -> opened branch metadata
        if len(path) == 0 or path == "/":
            return Ok({
                "name": "opened",
                "label": "Opened",
                "type": "folder",
                "category": "folder",
                "description": "Opened audio files"
            })

        # Device path: "/opened/0" -> delegate to device
        if len(path) >= 1:
            try:
                device_id = int(path[0])
                if device_id in self._soundfile_devices:
                    device = self._soundfile_devices[device_id]
                    subpath = path[1:]  # Strip device_id
                    return device.get_metadata(subpath)
            except ValueError:
                pass

        return Result.error(f"FilesystemManager: device not found at {path}")

    def _get_available_metadata(self, path: DataPath):
        """Get metadata for /available branch"""
        # Convert to string for comparisons
        print(path)
        if path == "/":
            return Ok({
                "name": "available",
                "label": "Available",
                "type": "folder",
                "category": "folder"
            })


        path_str = str(path)
        if path_str == "/fs-root":
            return Ok({
                "name": "fs-root",
                "label": "filesystem-root",
                "type": "shortcut",
                "category": "shortcut",
                "details": {
                    "fs-path": "/"
                }
            })

        if path_str == "/home":
            return Ok({
                "name": "home",
                "label": "home-dir",
                "type": "shortcut",
                "category": "shortcut",
                "details": {
                    "fs-path": str(Path.home())
                }
            })

        if path_str == "/mounts":
            return Ok({
                "name": "mounts",
                "label": "mounts",
                "type": "folder",
                "category": "folder",
                "description": "Mounted filesystems"
            })

        if path_str == "/bookmarks":
            return Ok({
                "name": "bookmarks",
                "label": "bookmarks",
                "type": "folder",
                "category": "folder",
                "description": "Bookmarked locations (to be implemented)"
            })

        # Check if node is under /mounts
        if path_str.startswith("/mounts/"):
            # Extract real path (strip /mounts prefix)
            # E.g., "/mounts/boot/efi" -> "/boot/efi"
            fs_path = path_str[len("/mounts"):]
        else:
            # Map virtual path to real filesystem path
            fs_path = self._map_virtual_to_real(path)

        # Check if path points to a channel (parent is audio file, last part is digit)
        if len(path) > 0:
            parent_path = path.dirname()
            parent_str = str(parent_path)

            # Get parent filesystem path
            if parent_str.startswith("/mounts/"):
                parent_fs_path = parent_str[len("/mounts"):]
            else:
                parent_fs_path = self._map_virtual_to_real(parent_path)

            # Check if parent exists and is an audio file
            if os.path.exists(parent_fs_path) and os.path.isfile(parent_fs_path):
                parent_info = _get_soundfile_info(str(parent_fs_path))
                if parent_info:
                    # Parent is audio file - check if this is a valid channel
                    try:
                        channel_idx = int(path[-1])
                        channels = parent_info[0]
                        if 0 <= channel_idx < channels:
                            # Valid channel
                            return Ok({
                                "name": str(channel_idx),
                                "label": f"Channel {channel_idx}",
                                "type": "audio-channel",
                                "category": "audio-channel",
                                "capabilities": {
                                    "openable": True,
                                    "readable": True,
                                    "writable": False
                                },
                                "details": {
                                    "channel-id": channel_idx,
                                    "sample-rate": parent_info[1],
                                    "frames": parent_info[2]
                                }
                            })
                    except (ValueError, IndexError):
                        pass

        if not os.path.exists(str(fs_path)):
            basename = os.path.basename(str(fs_path)) if os.path.basename(str(fs_path)) else str(fs_path)
            return Ok({
                "name": basename,
                "label": basename,
                "type": "error",
                "category": "error",
                "description": "Path does not exist"
            })

        basename = os.path.basename(str(fs_path)) if os.path.basename(str(fs_path)) else str(fs_path)

        if os.path.isdir(str(fs_path)):
            return Ok({
                "name": basename,
                "label": basename,
                "type": "folder",
                "category": "folder",
                "details": {
                    "fs-path": str(fs_path)
                }
            })

        # It's a file - check if it's a valid audio file
        info = _get_soundfile_info(str(fs_path))
        if info:
            channels, sample_rate, frames, fmt, subtype, endian = info
            duration = frames / sample_rate if sample_rate > 0 else 0
            return Ok({
                "name": basename,
                "label": basename,
                "type": "audio-file",
                "category": "audio-file",
                "description": f"{channels}ch, {sample_rate}Hz, {fmt}/{subtype}",
                "capabilities": {
                    "openable": True,
                    "readable": True,
                    "writable": False
                },
                "details": {
                    "file-path": str(fs_path),
                    "sample-rate": sample_rate,
                    "channels": channels,
                    "frames": frames,
                    "format": fmt,
                    "subtype": subtype,
                    "endian": endian,
                    "duration-seconds": duration
                },
                "config-schema": {
                    "file-path": {
                        "type": "str",
                        "default": str(fs_path),
                        "required": True,
                        "readonly": True,
                        "label": "File Path"
                    },
                    "full-load": {
                        "type": "bool",
                        "default": True,
                        "required": False,
                        "label": "Load Full File",
                        "description": "Load entire file into memory vs. streaming"
                    }
                }
            })
        else:
            # Not an audio file
            return Ok({
                "name": basename,
                "label": basename,
                "type": "file",
                "category": "file",
                "details": {
                    "fs-path": str(fs_path)
                }
            })

    def open(self, path: DataPath, params: Optional[Dict] = {}) -> Result:
        """Open a device or buffer.

        Args:
            path: Path to open (e.g., /available/fs-root/file.wav or /opened/0/0)
            params: Parameters for opening

        Returns:
            Result containing Device or Buffer
        """
        # Must be under /available branch for device creation
        if len(path) > 0 and path[0] == "available":
            # Opening a device from /available
            # Extract file path from params
            file_path = path[1:]
            if not file_path:
                return Result.error("file_path parameter required")

            full_load = params.get("full-load", True)
            channel = None

            print("type: ", type(path), path[1:], file_path, file_path[:-1], file_path._path)
            # wecheck if the path contains channel_id
            if os.path.isfile(str(file_path)):
                file_path = str(file_path)
            else:
                channel = file_path[-1]
                file_path = str(file_path[:-1])

            # Check if already opened
            for device_id, device in self._soundfile_devices.items():
                if device._file_path == file_path:
                    # TODO... this is not an error! the opened device should be returned!
                    return Result.error(f"File {file_path} already opened as device {device_id}")

            print(f"Opening file: {file_path}")
            # Create device
            res = SoundfileDevice.create(file_path, full_load)
            if not res:
                return Result.error(f"Failed to open {file_path}", res)
            device = res.unwrapped

            # Store device
            device_id = self._next_device_id
            self._next_device_id += 1
            self._soundfile_devices[device_id] = device

            if channel is None:
                return Ok(device)
            else:
                return device.open(DataPath("/") / str(channel), params)

        elif len(path) > 0 and path[0] == "opened":
            # Opening a buffer from /opened/device_id/channel_id
            if len(path) < 3:
                return Result.error("Invalid path for buffer open - need /opened/device_id/channel_id")

            try:
                device_id = int(path[1])
                channel_path = DataPath("/" + path[2])  # e.g., "/0"
            except ValueError:
                return Result.error("Invalid device_id")

            if device_id not in self._soundfile_devices:
                return Result.error(f"Device {device_id} not found")

            device = self._soundfile_devices[device_id]
            return device.open(channel_path, params)

        return Result.error(f"Invalid path for open: {path}")

    def set(self, path: DataPath, value) -> Result[None]:
        """Set not implemented"""
        return Result.error("SoundfileManager: set: not implemented")

    def add_child(self, path: DataPath, value) -> Result[None]:
        """Set not implemented"""
        return Result.error("SoundfileManager: add_child: not implemented")

    def configure(self, path: DataPath, params: dict) -> Result[None]:
        """Update parameters of an opened device or buffer.

        Args:
            path: Path to the asset
            params: Parameters to update

        Returns:
            Result[None]
        """
        # TODO: Implement configuration updates
        return Result.error("configure not implemented yet")

    def close(self, path: DataPath) -> Result[None]:
        """Close a device or buffer.

        Args:
            path: Path to close

        Returns:
            Result[None]
        """
        if len(path) > 0 and path[0] == "opened":
            if len(path) == 2:
                # Close entire device
                try:
                    device_id = int(path[1])
                    if device_id in self._soundfile_devices:
                        del self._soundfile_devices[device_id]
                        return Ok(None)
                except ValueError:
                    pass

            # TODO: Close individual buffers

        return Result.error(f"Invalid path for close: {path}")

    def as_tree(self, data_path: DataPath = None, depth: int = 0) -> Result[Union[dict]]:
        pass

def test():
    from pprint import pprint
    fs_manager = FilesystemManager()
    root = DataPath("/")

    #res = fs_manager.get_children_names(root / "available/home/tmp")
    #print(res.unwrapped)

    #res = fs_manager.get_metadata(root / "available/home/misi/tmp/Encore.mp3")

    #file = res.unwrapped

    #pprint(file)

    res = fs_manager.open(root / "available/home/misi/tmp/Encore.mp3/0")

    print(res)


    return
    print(f"root: {root}")

    res = plugin.get_metadata(root)
    if not res:
        print("error")
        return
    root_metadata = res.unwrapped
    pprint(root_metadata)
    root_children = plugin.get_children_names(root)
    print(f"root children: {root_children}")

if __name__ == "__main__":
    test()
