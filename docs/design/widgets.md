# Widget System Design

## Overview

The widget system provides a declarative YAML-based UI framework built on top of imgui_bundle. It implements a hierarchical widget architecture with data binding, event handling, and dynamic content generation.

## Architecture Pattern

The widget system follows a **Model-View-Controller (MVC)** pattern where:

- **Model**: TreeLike backends (DataTree, Kernel, Providers) - holds the application state
- **View**: Widget hierarchy defined in YAML - displays the data
- **Controller**: WidgetFactory + Event system - manages widget creation and user interactions

## Widget Lifecycle

### 1. Creation Phase

```
WidgetFactory.create_widget()
  → Widget.__init__()          # Initialize instance variables
  → Object.create()             # Static factory method
    → Widget.init()             # Initialize widget-specific state
      → _init_events()          # Parse event handlers from params
      → Create _activated widget if "activated" in params
```

### 2. Rendering Cycle

Every frame, `widget.render()` executes the following pipeline:

```
render()
  ├─ _prepare_render()         # Load metadata and create _activated widget
  │   ├─ Get metadata from TreeLike at _data_path
  │   ├─ Create FieldValues helper
  │   └─ Create _activated widget from "activated" param (if not created in init())
  │
  ├─ _push_styles()            # Apply ImGui style overrides
  │
  ├─ _pre_render()             # Widget-specific rendering (returns is_opened)
  │   └─ Call ImGui API (begin_table, button, text, etc.)
  │
  ├─ _detect_and_execute_events()  # Check ImGui state and execute event handlers
  │   ├─ on-active: if is_opened
  │   ├─ on-click: if is_item_clicked()
  │   ├─ on-double-click: if is_mouse_double_clicked()
  │   ├─ on-right-click: if is_item_clicked(1)
  │   └─ on-hover: if is_item_hovered()
  │
  ├─ if is_opened:
  │   ├─ _activated.render()   # Recursively render child widgets
  │   └─ _post_render()        # Widget-specific cleanup (tree_pop, end_table, etc.)
  │
  └─ _pop_styles()             # Remove style overrides
```

### 3. Disposal Phase

```
widget.dispose()               # Cleanup resources
  └─ _activated.dispose()      # Recursively dispose children
```

## Data Binding System

### Data Path Resolution

Widgets access data through the TreeLike interface using **ObjectPath**:

```
ObjectPath("/") → root of data tree
ObjectPath("/foo/bar") → absolute path
ObjectPath("foo/bar") → relative path (from current _data_path)
```

### data-id Parameter

The `data-id` parameter in YAML specifies which data node a widget should bind to:

```yaml
# Without data-path: widget uses parent's data path
- text:

# With data-path: widget uses /parent/child-name
- data-path: child-name
  text:

# Absolute path: widget uses /absolute/path
- data-path: /absolute/path
  text:
```

### FieldValues: Data Access Helper

`FieldValues` implements the logic for reading/writing widget field values (like "label"):

**Resolution order**:
1. **Static value in params**: `{label: "Static Text"}` → use "Static Text"
2. **data-map remapping**: `{data-map: {label: "/other/path"}}` → use value from remapped path
3. **Dynamic from TreeLike**: Query `get(data_path / "label")` from backend

**Example with data-map**:
```yaml
# Widget at path "/foo", but reads label from root "/selected"
- text:
    data-map:
      label: "/selected"  # Absolute path
```

This is analogous to **Model binding in MVC** where the View (widget) binds to specific Model properties (TreeLike paths).

### Kernel Demo Example: Selected Node Tracking

**File**: `demo_widgets.yaml` - `kernel-demo-popup`

```yaml
kernel-demo-popup:
  type: popup
  activated:
    - text: "Selected: "
    - same-line
    - text:
        data-map:
          label: "/selected"  # Bind to root metadata field "selected"
        style:
          text: [0.2, 1.0, 0.2, 1.0]
    - separator
    - kernel-recursive

kernel-recursive:
  type: composite
  body:
    - foreach-child:
        - tree-node:
            activated: kernel-recursive
            on-click: default
            data-map:
              selected: "/selected"  # Write selection to root
```

**Data Structure** (in `demo_widget.py`):
```python
kernel_data = {
    "metadata": {
        "selected": "(none)"  # Stored at root
    },
    "children": {
        "kernel": kernel  # TreeLike backend
    }
}
kernel_tree = DataTree(kernel_data)
```

**MVC Analogy**:
- **Model**: DataTree wrapping kernel + selection state at root
- **View**: Text widget displaying selected path, Tree widgets displaying kernel hierarchy
- **Controller**: on-click event updates `/selected` when tree node clicked

The selected value is stored **at the root** (`/selected`) rather than with each tree node, demonstrating **separation of View state (selection) from Model data (kernel tree)**. All tree-node widgets use `data-map: {selected: "/selected"}` to read/write the shared selection state.

## Widget Types

### Primitive Widgets

**Stateless widgets** that directly map to ImGui API calls:
- `text`, `bullet-text`, `separator-text`, `separator`, `same-line`
- `input-text`, `input-int`, `slider-int`, `slider-float`, `combo`, `checkbox`
- `button`, `menu-item`

### Container Widgets

**Stateful widgets** that manage child widget rendering:

**Tree Structure Widgets**:
- `tree-node`: Collapsible tree with `_pre_render()` → `tree_node()`, `_post_render()` → `tree_pop()`
- `collapsing-header`: Similar to tree-node, different visual style
- `menu`: Menu context with `begin_menu()` / `end_menu()`
- `indent`: Indentation context with `indent()` / `unindent()`

**Layout Widgets**:
- `table`: Table context with `begin_table()` / `end_table()`
- `row`: Table row with `table_next_row()`
- `column`: Table column with `table_next_column()`

**Special Widgets**:
- `popup`: Modal popup with `open_popup()` / `begin_popup()` / `end_popup()`
- `tooltip`: Hover tooltip with `begin_tooltip()` / `end_tooltip()`
- `implot`: Plot context with ImPlot API

### Composite Widget

**Meta-widget** that dynamically creates child widgets from YAML body:

```yaml
type: composite
body:
  - text: "Hello"
  - button: "Click"
  - foreach-child:  # Iterate over data children
      - text:
  - foreach-key:    # Iterate over metadata keys
      - text: "$key: $value"  # Template substitution
```

## Event System

### Event Types

- `on-active`: Widget returns True (opened/activated)
- `on-click`: Left mouse button click
- `on-double-click`: Double-click
- `on-right-click`: Right mouse button click
- `on-hover`: Mouse hover

### Event Actions

**show**: Display a widget (popup/tooltip)
```yaml
on-click:
  show: my-popup
```

**dispatch**: Fire an event to dispatcher
```yaml
on-click:
  dispatch:
    message: "selection-changed"
    data: {path: "/foo"}
```

**default**: Widget-specific default action (e.g., tree-node selection)
```yaml
on-click: default
```

### Conditional Events

Events can have `when` conditions based on metadata:

```yaml
on-click:
  show: config-popup
  when:
    openable: true  # Only show if metadata.openable == true
```

## Dynamic Content Generation

### foreach-child

Iterates over TreeLike children, creating widgets for each:

```yaml
foreach-child:
  - tree-node:
      activated: recursive-template
```

**Example**: Renders all children at current data path as tree nodes.

### foreach-key

Iterates over metadata keys, creating widgets with `$key` and `$value` substitution:

```yaml
foreach-key:
  - text: "$key: $value"
```

**Example**: Display all metadata entries as "name: value" text.

## Style System

Widgets can override ImGui styles via the `style` parameter:

```yaml
text:
  style:
    text: [1.0, 0.0, 0.0, 1.0]  # Red text color
```

Style names use kebab-case (converted to ImGuiCol_ enums):
- `text` → `ImGuiCol_.text`
- `button` → `ImGuiCol_.button`
- `button-hovered` → `ImGuiCol_.button_hovered`

Styles are pushed before `_pre_render()` and popped after `_post_render()`.

## Widget Factory

**Responsibilities**:
1. Load YAML widget definitions from `layouts/*.yaml`
2. Cache primitive widget classes
3. Resolve widget names with namespace support
4. Create widget instances via `Widget.create()`

**Namespace Resolution**:
```python
# YAML: demo_widgets.yaml defines "my-widget"
# Full name: "demo_widgets.my-widget"

# Smart lookup:
factory.create_widget("demo_widgets.text", ...)  # → text primitive
factory.create_widget("demo_widgets.my-widget", ...)  # → custom widget
```

## File Organization

```
src/waew/frontend/
├── widget.py           # Base Widget class, FieldValues
├── composite.py        # Composite widget (dynamic child creation)
├── widgets.py          # Primitive widgets (Text, Button, etc.)
├── table.py            # Table layout widgets (Table, Row, Column)
├── implot.py           # ImPlot widgets (Implot, ImplotLayer, ImplotGroup)
├── widget_factory.py   # WidgetFactory (loads YAML, creates widgets)
├── layouts/            # YAML widget definitions
│   ├── demo_widgets.yaml
│   ├── layer-config.yaml
│   └── alsa-device.yaml
└── demo_widget.py      # Demo application
```

## Best Practices

### 1. Data Separation
Store **transient UI state** (selection, expanded nodes) at the root of DataTree, separate from domain data:

```python
data = {
    "metadata": {
        "selected": "/path",  # UI state
        "expanded": {...}
    },
    "children": {
        "domain_data": {...}  # Domain data
    }
}
```

### 2. data-map for Shared State
Use `data-map` with absolute paths to share state across widgets:

```yaml
- tree-node:
    data-map:
      selected: "/selected"  # All nodes share selection
```

### 3. Recursive Templates
Define recursive widgets for tree structures:

```yaml
tree-recursive:
  type: composite
  body:
    - foreach-child:
        - tree-node:
            activated: tree-recursive  # Self-reference
```

### 4. Event-Driven Updates
Use events to decouple widgets from backend logic:

```yaml
on-click:
  dispatch:
    message: "item-selected"
    data: {path: "$path"}
```

## Performance Considerations

- **Lazy Widget Creation**: `_activated` widget created on first render, not in `init()`
- **Metadata Caching**: `_metadata` loaded once per render cycle in `_prepare_render()`
- **Style Push/Pop**: Efficient ImGui style stack management
- **Buffer Locking**: ImPlot layers use try_lock() to avoid blocking on busy buffers

## Future Extensions

- **Layout Widgets**: HBox, VBox for automatic layout
- **Data Validation**: Schema validation for input widgets
- **Animation System**: Transition animations for state changes
- **Hot Reload**: Dynamic YAML reload without restart
