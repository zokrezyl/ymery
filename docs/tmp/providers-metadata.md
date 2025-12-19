# Provider Metadata Analysis and Standardization Recommendations

This document analyzes metadata fields across all providers in both ymery and waew codebases.

## Analysis Date
2025-12-08

---

## 1. YMERY WAVEFORM PROVIDER

### WaveformManager (Provider Root)
**Path:** `/`
- name: "waveform"
- label: "Waveform Generator"
- type: "provider"

### Category Nodes
**Path:** `/available`, `/opened`
- name: "available" | "opened"
- label: "Available" | "Opened"
- type: "category"

### Waveform Endpoint Nodes (Available)
**Path:** `/available/sine`, `/available/square`, `/available/triangle`
- name: waveform_type (e.g., "sine")
- label: "{waveform_type} Wave"
- type: "waveform-endpoint"
- openable: True
- info:
  - waveform_type

### Channel Nodes (Available)
**Path:** `/available/sine/0`
- name: "0"
- label: "Channel 0"
- type: "waveform-channel"
- info:
  - channel_id: 0
  - waveform_type

### Device Nodes (Opened)
**Path:** `/opened/sine`
- name: waveform_type
- label: "{waveform_type} ({frequency}Hz)"
- path: str(path)
- type: "waveform-channel"
- info:
  - waveform_type
  - frequency
  - sample_rate
  - running
- instance: buffer_mediator

---

## 2. WAEW FILESYSTEM PROVIDER

### FilesystemManager (Provider Root)
**Path:** `/`
- name: "filesystem"
- label: "filesystem"
- type: "provider"
- description: "filesystem"

### Category Nodes
**Path:** `/available`, `/opened`
- name: "available" | "opened"
- label: "available" | "opened"
- type: "category"
- description: "Available audio files" | "Opened audio files"

### Shortcut Nodes
**Path:** `/available/fs-root`, `/available/home`
- name: "fs-root" | "home"
- label: "fs-root" | "home"
- path: path_str
- type: "shortcut"
- fs-path: "/" | str(Path.home())

### Category Nodes (Mounts/Bookmarks)
**Path:** `/available/mounts`, `/available/bookmarks`
- name: "mounts" | "bookmarks"
- label: "mounts" | "bookmarks"
- path: path_str
- type: "category"
- description: "Mounted filesystems" | "Bookmarked locations (to be implemented)"

### Directory Nodes
**Path:** `/available/fs-root/some/directory`
- name: basename
- label: basename
- path: path_str
- fs_path: real_fs_path
- type: "directory"

### Audio File Nodes
**Path:** `/available/fs-root/some/file.wav`
- name: basename
- label: basename
- path: path_str
- fs_path: real_fs_path
- type: "audio-file"
- category: "device"
- openable: True
- info:
  - samplerate
  - channels
  - frames
  - format
  - subtype
  - endian
- open-arguments:
  - file_path (type: str, default-value: fs_path)
  - full_load (type: bool, default-value: True)

### Channel Nodes (Available)
**Path:** `/available/fs-root/file.wav/0`
- name: "channel-{idx}"
- label: "channel-{idx}"
- path: path_str
- type: "channel"
- info:
  - channel_id
  - samplerate
  - frames

### Device Nodes (Opened - SoundfileDevice)
**Path:** `/opened/0`
- name: basename
- label: basename
- path: str(path)
- type: "soundfile-device"
- info:
  - file_path
  - channels
  - samplerate
  - frames

### Channel Nodes (Opened)
**Path:** `/opened/0/0`
- name: "channel-{ch}"
- label: "channel-{ch}"
- path: str(path)
- type: "channel"
- info:
  - channel_id
- instance: mediator

---

## 3. WAEW ALSA PROVIDER

### AlsaManager (Provider Root)
**Path:** `/`
- name: "alsa"
- label: "ALSA"
- type: "provider"

### Category Nodes
**Path:** `/available`, `/opened`
- name: "available" | "opened"
- label: "Available" | "Opened"
- type: "category"

### Category Nodes (Cards/PCMs)
**Path:** `/available/cards`, `/available/pcms`
- name: "cards" | "pcms"
- label: "cards" | "pcms"
- type: "category"

### Card Nodes
**Path:** `/available/cards/0`
- name: str(card_idx)
- label: card_info["name"]
- type: "card"

### Device Nodes (Hardware)
**Path:** `/available/cards/0/0`
- name: str(device_idx)
- label: device_info["name"]
- type: "device"

### Subdevice Nodes (Openable)
**Path:** `/available/cards/0/0/0`
- name: str(subdevice_idx)
- label: subdevice_info["name"]
- type: "subdevice"
- openable: True
- info:
  - card: card_name
  - device: device_name
  - card_num
  - device_num
  - subdevice_num
  - channels: [min, max]
  - rate: [rates...]
  - formats: [format_strings...]
- open-arguments:
  - device (type: str, default-value: device_str, readonly: True)
  - subdevice (type: int, default-value: subdevice_idx, readonly: True)
  - num_channels (type: int, default-value: channels[1], min: channels[0], max: channels[1])
  - sample_rate (type: int, default-value: rate[1], choices: rate)
  - format (type: str, default-value: formats[0], choices: formats)
  - period_size (type: int, default-value: 1024, min: 128, max: 8192)
- form-layout: "alsa-device"

### Channel Nodes (Available)
**Path:** `/available/cards/0/0/0/0`
- name: str(channel_idx)
- label: "Channel {channel_idx}"
- type: "channel"

### Device Nodes (Opened - AlsaDevice)
**Path:** `/opened/cards/0/0/0`
- name: device
- path: path
- type: "alsa-device"
- info:
  - device
  - subdevice
  - num_channels
  - sample_rate
  - period_size
  - running

### Category Node (Channels within opened device)
**Path:** `/opened/cards/0/0/0/channels`
- name: "Channels"
- path: path
- type: "category"

### Channel Nodes (Opened)
**Path:** `/opened/cards/0/0/0/channels/0`
- name: "channel-{ch}"
- label: "channel-{ch}"
- path: str(path)
- type: "channel"
- info:
  - channel_id
- instance: mediator

---

## 4. WAEW JACK PROVIDER

### JackManager (Provider Root)
**Path:** `/`
- name: "jack"
- label: "jack"
- description: "Jack connectivity provider"

### Category Nodes
**Path:** `/available`, `/opened`
- name: "available" | "opened"
- label: "available" | "opened"
- type: "category"
- description: "Available JACK clients" | "Opened JACK clients"

### Manual Client Node
**Path:** `/available/client`
- name: "Create JACK Client"
- label: "Create JACK Client"
- path: path
- type: "manual-client"
- openable: True
- open-arguments:
  - client_name (type: str, default-value: "waew_client")
  - server_name (type: str, default-value: "default")
  - num_channels (type: int, default-value: 2)
- provider-class: JackClientDevice

### Category Node (Readable Clients)
**Path:** `/available/readable-clients`
- name: "Readable Clients"
- label: "Readable Clients"
- path: path
- type: "category"
- description: "JACK clients with output ports available for capture"

### Client Nodes (Auto-connect)
**Path:** `/available/readable-clients/system`
- name: "{client_name} ({num_ports} ports)"
- label: "{client_name} ({num_ports} ports)"
- path: path
- type: "client"
- openable: True
- info:
  - ports: [port_names...]
  - num_ports
- open-arguments: {}

### Port Nodes
**Path:** `/available/readable-clients/system/capture_1`
- name: port_name
- label: port_name
- path: path
- type: "client"
- openable: True
- open-arguments: {}

### Device Nodes (Opened - JackClientDevice)
**Path:** `/opened/waew-client-abc123`
- name: client_name
- label: client_name
- path: str(path)
- type: "jack-device"
- info:
  - num_channels
  - sample_rate
  - buffer_size
  - running

### Channel Nodes (Opened)
**Path:** `/opened/waew-client-abc123/input_0`
- name: port.name
- label: path[0]
- path: str(path)
- type: "channel"
- info:
  - port_name
- instance: mediator

---

## INCONSISTENCIES IDENTIFIED

### 1. Field Name Variations
- **name** vs **label**: Sometimes duplicate, sometimes different
- **path** field: Present in some, missing in others
- **description** vs **info**: Overlapping purposes
- **category** field: Only in filesystem provider audio-file

### 2. Type Field Values
- Inconsistent naming: "waveform-channel" vs "channel"
- "audio-file" has category="device" (confusing duplication)
- "jack-device" vs "alsa-device" vs "soundfile-device" (inconsistent naming)
- "client" used for port nodes (misleading)

### 3. Openable Field
- Missing in many openable nodes (waveform endpoints)
- Present but redundant when open-arguments exists

### 4. Info vs Top-Level Fields
- Some put everything in info {}, others at top level
- Sample rate: sometimes "samplerate", sometimes "sample_rate"

### 5. Instance Field
- Only added to opened devices/channels
- Inconsistent presence

---

## STANDARDIZATION RECOMMENDATIONS

### Core Fields (ALL NODES)
- **uid**: Unique identifier from Object.uid (e.g., "waveform-manager-abc123def456")
- **label**: Human-readable display name (what user sees)
- **type**: Actual class name (e.g., "waveform-manager", "alsa-device", "soundfile-device")
- **category**: Semantic grouping for UI layer (e.g., "audio-device", "audio-channel", "folder")
- **path**: Full path string (for debugging/logging)

### Optional Core Fields
- **description**: Brief text description (for tooltips, help text)
- **status**: Runtime status info (e.g., "running", "stopped", "error")

### Type Field (Actual Class Names)
The `type` field should reflect the actual Python class implementing the node:

**Provider Manager Classes:**
- **type: "waveform-manager"**: WaveformManager
- **type: "alsa-manager"**: AlsaManager
- **type: "jack-manager"**: JackManager
- **type: "filesystem-manager"**: FilesystemManager

**Device Classes:**
- **type: "waveform-device"**: WaveformDevice
- **type: "alsa-device"**: AlsaDevice
- **type: "jack-device"**: JackClientDevice
- **type: "soundfile-device"**: SoundfileDevice

**Other Classes:**
- **type: "dynamic-audio-buffer-mediator"**: DynamicAudioBufferMediator
- **type: "static-audio-buffer-mediator"**: StaticAudioBufferMediator

### Category Field (Semantic UI Grouping)
The `category` field provides semantic meaning for UI widgets and ImGui layers:

**Organizational Categories:**
- **category: "folder"**: Organizational grouping (replaces "category") - e.g., "available", "opened", "cards", "mounts"
- **category: "shortcut"**: Virtual shortcut/link

**Resource Categories:**
- **category: "audio-device"**: Any audio device (openable or opened)
- **category: "audio-channel"**: Individual audio channel
- **category: "audio-file"**: Audio file on filesystem
- **category: "hardware-card"**: Hardware card (ALSA)
- **category: "hardware-device"**: Hardware device (ALSA)

**UI widgets should key off `category` field:**
- Show folder icon for `category: "folder"`
- Show device icon for `category: "audio-device"`
- Show channel icon for `category: "audio-channel"`
- Enable audio operations for `category: "audio-channel"`

### Capability Fields
Instead of scattered flags, use structured capability object:

**capabilities:**
- **openable**: bool (can be opened)
- **configurable**: bool (can be configured)
- **closeable**: bool (can be closed)
- **readable**: bool (provides audio data)
- **writable**: bool (accepts audio data)

### Technical Details Object
Replace scattered "info" with structured "details":

**details:**
- **sample-rate**: int (Hz, consistent naming with dash)
- **channels**: int or [min, max] (number of audio channels)
- **frames**: int (total frames, for files)
- **buffer-size**: int (buffer/period size)
- **format**: str (audio format)
- **device-path**: str (hardware device path)
- **file-path**: str (filesystem path)
- **running**: bool (runtime status)
- [any other provider-specific technical info]

### Configuration Schema
Replace "open-arguments" with structured "config-schema":

**config-schema:**
- **{parameter-name}**:
  - **type**: str | int | float | bool
  - **default**: default value
  - **min**: minimum value (for numeric)
  - **max**: maximum value (for numeric)
  - **choices**: [valid values] (for enum)
  - **required**: bool
  - **readonly**: bool
  - **label**: human-readable parameter name
  - **description**: parameter description

### Instance Reference
- **instance**: Reference to actual backend object (mediator, buffer, etc.)
  - Only present for opened resources
  - Keep as is (already consistent)

---

## PROPOSED STANDARD METADATA STRUCTURE

### Example 1: Device Manager
```python
{
    "uid": "alsa-manager-xyz789abc123",
    "label": "ALSA Audio",
    "type": "alsa-manager",
    "category": "audio-device-manager",
    "description": "Advanced Linux Sound Architecture audio interface"
}
```

### Example 2: Folder (Organizational)
```python
{
    "uid": "folder-available-abc123",
    "label": "Available Devices",
    "type": "folder",
    "category": "folder",
    "description": "Audio devices available to open"
}
```

### Example 3: Audio Device (Available, Openable ALSA Device)
```python
{
    "uid": "alsa-device-def456ghi789",
    "label": "USB Audio Device (Stereo)",
    "type": "alsa-device",
    "category": "audio-device",
    "description": "USB audio input device, 2 channels @ 48kHz",
    "capabilities": {
        "openable": True,
        "configurable": False,
        "readable": True,
        "writable": False
    },
    "details": {
        "card": "USB Audio",
        "device": "USB Audio Device",
        "card-num": 0,
        "device-num": 0,
        "subdevice-num": 0,
        "channels": [1, 2],
        "sample-rate-options": [44100, 48000, 96000],
        "format-options": ["S16_LE", "S24_LE", "S32_LE", "FLOAT_LE"]
    },
    "config-schema": {
        "device": {
            "type": "str",
            "default": "hw:0,0,0",
            "required": True,
            "readonly": True,
            "label": "Device Path"
        },
        "num-channels": {
            "type": "int",
            "default": 2,
            "min": 1,
            "max": 2,
            "required": True,
            "label": "Number of Channels"
        },
        "sample-rate": {
            "type": "int",
            "default": 48000,
            "choices": [44100, 48000, 96000],
            "required": True,
            "label": "Sample Rate"
        },
        "format": {
            "type": "str",
            "default": "S16_LE",
            "choices": ["S16_LE", "S24_LE", "S32_LE", "FLOAT_LE"],
            "required": True,
            "label": "Audio Format"
        },
        "period-size": {
            "type": "int",
            "default": 1024,
            "min": 128,
            "max": 8192,
            "required": False,
            "label": "Period Size"
        }
    }
}
```

### Example 4: Audio Device (Opened Waveform Device)
```python
{
    "uid": "waveform-device-jkl012mno345",
    "label": "Sine Wave (440Hz)",
    "type": "waveform-device",
    "category": "audio-device",
    "status": "running",
    "capabilities": {
        "openable": False,
        "configurable": True,
        "closeable": True,
        "readable": True,
        "writable": False
    },
    "details": {
        "waveform-type": "sine",
        "frequency": 440.0,
        "sample-rate": 48000,
        "buffer-size": 1024
    },
    "instance": <buffer_mediator>
}
```

### Example 5: Audio Channel
```python
{
    "uid": "audio-channel-pqr678stu901",
    "label": "Channel 0 (Left)",
    "type": "audio-channel",
    "category": "audio-channel",
    "status": "active",
    "capabilities": {
        "openable": True,
        "readable": True,
        "writable": False
    },
    "details": {
        "channel-id": 0,
        "channel-name": "Left"
    },
    "instance": <mediator>
}
```

### Example 6: Audio File
```python
{
    "uid": "audio-file-vwx234yz567",
    "label": "recording.wav",
    "type": "audio-file",
    "category": "audio-file",
    "description": "24-bit WAV file, stereo, 5:32 duration",
    "capabilities": {
        "openable": True,
        "readable": True,
        "writable": False
    },
    "details": {
        "file-path": "/home/user/recordings/recording.wav",
        "sample-rate": 48000,
        "channels": 2,
        "frames": 15974400,
        "format": "WAV",
        "subtype": "PCM_24",
        "duration-seconds": 332.8
    },
    "config-schema": {
        "file-path": {
            "type": "str",
            "default": "/home/user/recordings/recording.wav",
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
}
```

---

## MIGRATION STRATEGY

### Phase 1: Add New Fields (Non-Breaking)
1. Add new standard fields alongside existing ones
2. Keep all existing fields for backward compatibility
3. Update frontend to use new fields when available, fall back to old

### Phase 2: Update All Providers
1. Update each provider to emit new standard metadata
2. Keep old fields for backward compatibility
3. Test thoroughly with existing layouts

### Phase 3: Update Frontend/Widgets
1. Update all widgets to consume new metadata format
2. Remove fallback code for old fields
3. Test all demo applications

### Phase 4: Remove Old Fields
1. Remove old field generation from providers
2. Clean up any remaining references
3. Final testing pass

---

## SUMMARY OF KEY CHANGES

### Use Dashes, Not Underscores
- `sample-rate` not `sample_rate` or `samplerate` (NOTE: "samplerate" is NOT an English word!)
- `file-path` not `file_path`
- `channel-id` not `channel_id`
- `buffer-size` not `buffer_size`

### Core Field Structure
- **uid**: From Object.uid (unique identifier)
- **label**: Human-readable display name
- **type**: Actual Python class name (e.g., "alsa-manager", "waveform-device")
- **category**: Semantic grouping for UI (e.g., "audio-device", "audio-channel", "folder")
- **NOTE**: No `path` field! A node should not be aware of where it is in the hierarchy.

### Type Field = Class Name
- `waveform-manager` for WaveformManager
- `alsa-manager` for AlsaManager
- `jack-manager` for JackManager
- `filesystem-manager` for FilesystemManager
- `waveform-device` for WaveformDevice
- `alsa-device` for AlsaDevice
- `jack-device` for JackClientDevice
- `soundfile-device` for SoundfileDevice
- `audio-channel` for channel objects
- `folder` for organizational groupings

### Category Field = UI Semantic Grouping
- `audio-device-manager` for device managers
- `folder` for organizational nodes (NOT "category"!)
- `audio-device` for all audio devices
- `audio-channel` for all channels
- `audio-file` for audio files
- `shortcut` for virtual shortcuts

**Note**: ALSA cards and hardware devices are NOT exposed as separate abstractions. The ymery `audio-device` abstraction encompasses them. ALSA-specific metadata (card-num, device-num, subdevice-num) goes in the `details` object.

**UI widgets key off `category` field:**
- Folder icon for `category: "folder"`
- Device icon for `category: "audio-device"`
- Channel icon for `category: "audio-channel"`
- Enable audio ops for `category: "audio-channel"`

### Structured Objects
- `capabilities` for all capability flags (openable, readable, writable, etc.)
- `details` for all technical information (sample-rate, channels, frames, etc.)
- `config-schema` for all configuration parameters (type, default, min, max, choices)

### Clear Separation
- Available resources: describe what CAN be opened
- Opened resources: describe what IS opened
- Both use same core field structure

This standardization will make the codebase much more maintainable and the UI more predictable!

---

## DEVICE AND CHANNEL OPENING LOGIC

### Core Concepts

The relationship between DeviceManager, Device, Channel, and Buffer follows a clear hierarchy:

```
DeviceManager (AlsaManager, JackManager, etc.)
  └─> Device (AlsaDevice, JackDevice, etc.)
       └─> Channel (audio-channel)
            └─> Buffer (MediatedBuffer)
```

### Opening Workflow

#### Typical Use Case: Opening a Channel (Most Common)
When a user opens a channel through the UI:

1. **User Action**: User clicks "open" on a channel node (e.g., `/available/cards/0/0/0/channels/0`)
2. **DeviceManager Checks**: DeviceManager checks if parent Device is already opened
3. **Auto-Open Device**: If Device not opened, DeviceManager automatically opens it first
4. **Open Channel**: DeviceManager delegates to Device.open(channel_path, config)
5. **Return Buffer**: Device returns MediatedBuffer for that channel
6. **UI Update**: Channel appears in `/opened/...` tree with `instance: <mediator>`

**Result**: User gets a buffer, device was opened transparently.

#### Rare Use Case: Opening a Device Directly
When a user explicitly opens a device (rare):

1. **User Action**: User clicks "open" on device node (e.g., `/available/cards/0/0/0`)
2. **DeviceManager Opens**: DeviceManager creates Device instance
3. **Device Init**: Device initializes, creates internal channel structures
4. **Return Device**: DeviceManager returns Device object
5. **UI Update**: Device appears in `/opened/...` tree

**Result**: Device is opened, but no buffers are created yet. Channels still need to be opened individually.

### Metadata for Available (Unopened) Nodes

#### Available Device Metadata
```python
{
    "uid": "alsa-device-abc123",
    "label": "USB Audio (Stereo)",
    "type": "alsa-device",
    "category": "audio-device",
    "description": "USB audio device, 2 channels @ 48kHz",
    "capabilities": {
        "openable": True,
        "configurable": False,
        "readable": True,
        "writable": False
    },
    "details": {
        "card": "USB Audio",
        "device": "USB Audio Device",
        "card-num": 0,
        "device-num": 0,
        "subdevice-num": 0,
        "channels": [1, 2],  # min, max
        "sample-rate-options": [44100, 48000, 96000],
        "format-options": ["S16_LE", "S24_LE", "FLOAT_LE"]
    },
    "config-schema": {
        "device": {
            "type": "str",
            "default": "hw:0,0,0",
            "required": True,
            "readonly": True,
            "label": "ALSA Device"
        },
        "num-channels": {
            "type": "int",
            "default": 2,
            "min": 1,
            "max": 2,
            "required": True,
            "label": "Number of Channels"
        },
        "sample-rate": {
            "type": "int",
            "default": 48000,
            "choices": [44100, 48000, 96000],
            "required": True,
            "label": "Sample Rate"
        },
        "period-size": {
            "type": "int",
            "default": 1024,
            "min": 128,
            "max": 8192,
            "required": False,
            "label": "Period Size"
        }
    }
}
```

**Key Points:**
- `capabilities.openable: True` - Can be opened
- `config-schema` - Shows what parameters are needed to open
- `details` - Provides technical information about the device
- **NO** `instance` field (not opened yet)
- **NO** `status` field (not running yet)

#### Available Channel Metadata
```python
{
    "uid": "audio-channel-def456",
    "label": "Channel 0",
    "type": "audio-channel",
    "category": "audio-channel",
    "description": "Left channel",
    "capabilities": {
        "openable": True,
        "readable": True,
        "writable": False
    },
    "details": {
        "channel-id": 0,
        "channel-name": "Left"
    }
}
```

**Key Points:**
- Minimal metadata - most details come from parent device
- `capabilities.openable: True` - Can be opened
- **NO** `config-schema` (uses parent device's config)
- **NO** `instance` field (not opened yet)

### Metadata for Opened Nodes

#### Opened Device Metadata
```python
{
    "uid": "alsa-device-abc123",
    "label": "USB Audio (Stereo)",
    "type": "alsa-device",
    "category": "audio-device",
    "status": "running",
    "capabilities": {
        "openable": False,  # Already opened
        "configurable": True,  # Can reconfigure
        "closeable": True,
        "readable": True,
        "writable": False
    },
    "details": {
        "card": "USB Audio",
        "device": "USB Audio Device",
        "card-num": 0,
        "device-num": 0,
        "subdevice-num": 0,
        "num-channels": 2,  # Actual opened value
        "sample-rate": 48000,  # Actual opened value
        "period-size": 1024,  # Actual opened value
        "format": "FLOAT_LE"  # Actual opened value
    },
    "instance": <device_object>  # Reference to actual Device instance
}
```

**Key Points:**
- `status: "running"` - Device is active
- `capabilities.openable: False` - Already opened
- `capabilities.closeable: True` - Can be closed
- `details` - Contains ACTUAL running config (not options)
- `instance` - Reference to Device object

#### Opened Channel Metadata
```python
{
    "uid": "audio-channel-def456",
    "label": "Channel 0 (Left)",
    "type": "audio-channel",
    "category": "audio-channel",
    "status": "active",
    "capabilities": {
        "openable": False,  # Already opened
        "closeable": True,
        "readable": True,
        "writable": False
    },
    "details": {
        "channel-id": 0,
        "channel-name": "Left",
        "buffer-frames": 4096,  # Current buffer size
        "sample-rate": 48000  # Inherited from device
    },
    "instance": <mediator>  # Reference to MediatedBuffer
}
```

**Key Points:**
- `status: "active"` - Channel is streaming
- `capabilities.openable: False` - Already opened
- `instance` - Reference to MediatedBuffer (this is what user actually uses!)
- `details` - Runtime information about the buffer

### Summary: Available vs Opened

| Field | Available | Opened |
|-------|-----------|--------|
| `uid` | ✓ | ✓ (same) |
| `label` | ✓ | ✓ (same or enhanced) |
| `type` | ✓ | ✓ (same) |
| `category` | ✓ | ✓ (same) |
| `description` | ✓ | optional |
| `capabilities.openable` | True | False |
| `capabilities.closeable` | False | True |
| `status` | ✗ | ✓ ("running", "active") |
| `details` | Options/ranges | Actual values |
| `config-schema` | ✓ (for device) | ✗ |
| `instance` | ✗ | ✓ (Device or Mediator) |

### Opening Paths

#### When Opening Device Directly (Rare)
```
User clicks: /available/cards/0/0/0
DeviceManager.open("/available/cards/0/0/0", config) → Device
Device appears at: /opened/cards/0/0/0
Result: Device object (no buffers yet)
```

#### When Opening Channel (Common)
```
User clicks: /available/cards/0/0/0/channels/0
DeviceManager checks: Is device at /opened/cards/0/0/0 open?
  - If NO: DeviceManager.open("/available/cards/0/0/0", config) → Device
  - Device appears at: /opened/cards/0/0/0
Then: Device.open("/channels/0", {}) → MediatedBuffer
Channel appears at: /opened/cards/0/0/0/channels/0
Result: MediatedBuffer for channel 0
```

### Key Insights

1. **Channel opening is the primary use case** - Users almost always want buffers, not bare devices
2. **Devices auto-open when needed** - Transparent to user, makes workflow simpler
3. **`instance` field is critical** - It's the actual object reference that other code uses
4. **Metadata evolves from available → opened** - Same structure, different values
5. **No `path` field** - Nodes don't know their location, DataTree manages hierarchy
6. **`config-schema` only for openable nodes** - Once opened, actual values in `details`


