# Imery YAML Language Guide

Imery is a declarative UI framework for Dear ImGui using YAML. This guide covers the complete YAML-based language for building ImGui applications.

## File Structure

A complete Imery application consists of YAML files with four top-level sections:

```yaml
import:        # Module imports
widgets:       # Widget definitions
data:          # Data tree definitions
app:           # Application configuration
```

**Note:** All sections are optional in any given module file. When multiple modules are loaded, their contents are merged:
- `widgets` definitions accumulate across all modules
- `data` definitions accumulate across all modules
- `import` statements are processed to load additional modules
- Only one `app` section is allowed across all modules

## Module System

### Imports

Import other YAML modules to use their widgets:

```yaml
import:
  - widgets              # imports widgets.yaml
  - utils.helpers        # imports utils/helpers.yaml
```

The `builtin` module is always automatically imported.

### Namespacing

Widgets are namespaced by their module name:
- Widget `main-window` in `app.yaml` becomes `app.main-window`
- Widget `demo-popup` in `widgets.yaml` becomes `widgets.demo-popup`

Reference widgets with full namespace or let the system resolve:
```yaml
body: widgets.my-popup    # explicit namespace
body: my-popup            # resolved within current namespace
```

**Directory-based namespacing:** Subdirectories introduce additional namespace levels, similar to Python packages:
- `utils/helpers.yaml` → namespace `utils.helpers`
- Widget `format` in that file → `utils.helpers.format`

**Namespace resolution:** When a widget name has no namespace (no `.`), the system first searches in the current module's namespace, then falls back to primitive widgets.

## Application Configuration

The `app` section defines the entry point:

```yaml
app:
  widget: app.main-window   # Root widget (with namespace)
  data: demo-data           # Root data node name
```

## Data Tree

The `data` section defines the hierarchical data structure:

```yaml
data:
  my-data:                    # Root data node name
    metadata:                 # Key-value pairs for this node
      label: "Root Node"
      selection: null
    children:                 # Child nodes
      child1:
        metadata:
          label: "First Child"
        children:
          grandchild:
            metadata:
              label: "Grandchild"
```

### Metadata

Metadata is a dictionary of key-value pairs accessible by widgets:
- `label`: Primary text value (used by most widgets)
- Custom keys: Any application-specific data

### Special Values

- `$kernel`: Substituted with the kernel TreeLike at runtime

## Widget Definitions

### Basic Structure

```yaml
widgets:
  my-widget:
    type: composite          # Widget type (required)
    body:                    # Child widgets
      - text: "Hello"
      - button:
          label: "Click Me"
```

### Widget Types

#### Primitive Widgets (no body)

| Widget | Description | Parameters |
|--------|-------------|------------|
| `text` | Display text | `label` |
| `bullet-text` | Text with bullet | `label` |
| `separator` | Horizontal line | - |
| `separator-text` | Line with text | `label` |
| `same-line` | Next widget on same line | - |
| `button` | Clickable button | `label`, `body` |
| `checkbox` | Boolean toggle | `label` |
| `combo` | Dropdown list | `label`, `items` |
| `radio-button` | Radio selection | `label`, `value` |

#### Container Widgets (with body)

**Note:** `button` is both a primitive and a container widget. When clicked, it renders its `body` content (typically a popup or other widget). This pattern is common in ImGui where a "head" widget (button) activates a "body" widget (popup).

| Widget | Description | Parameters |
|--------|-------------|------------|
| `composite` | Generic container | `body` |
| `tree-node` | Expandable tree item | `label`, `body` |
| `collapsing-header` | Collapsible section | `label`, `body`, `flags` |
| `group` | Logical grouping | `body` |
| `child` | Scrollable region | `body`, `size`, `border`, `flags` |
| `columns` | Column layout | `count`, `border`, `body` |
| `popup` | Context popup | `body` |
| `popup-modal` | Modal dialog | `label`, `body` |
| `tooltip` | Hover tooltip | `body` |

#### Input Widgets

| Widget | Description | Parameters |
|--------|-------------|------------|
| `input-text` | Text input | `label` |
| `input-int` | Integer input | `label` |
| `slider-int` | Integer slider | `label`, `min`, `max` |
| `slider-float` | Float slider | `label`, `min`, `max` |
| `color-edit` | Color picker | `label` |

#### Layout Widgets

| Widget | Description | Parameters |
|--------|-------------|------------|
| `tab-bar` | Tab container | `label`, `body` |
| `tab-item` | Single tab | `label`, `body` |
| `table` | Data table | `columns`, `body` |
| `draggable` | Draggable widget | `position`, `size`, `body` |

#### Menu Widgets

| Widget | Description | Parameters |
|--------|-------------|------------|
| `menu-bar` | Application menu bar | `body` |
| `menu` | Menu dropdown | `label`, `body` |
| `menu-item` | Clickable menu action | `label` |

#### Main Window Types

| Widget | Description |
|--------|-------------|
| `imgui-main-window` | Classic ImGui main window |
| `hello-imgui-main-window` | HelloImGui with docking support |

## Body Specification

The `body` parameter defines child widgets. It supports multiple formats.

**Internal implementation:** When you specify a `body`, the framework internally creates a `composite` widget to contain the children. This happens automatically for all widgets with a body, except for `composite` itself which directly uses the body content.

### String (Simple Widget)
```yaml
body: separator
```

### Dict (Widget with Params)
```yaml
body:
  text:
    label: "Hello"
    style:
      text: [1.0, 0.0, 0.0, 1.0]
```

### List (Multiple Widgets)
```yaml
body:
  - text: "Line 1"
  - separator
  - text: "Line 2"
```

### Compact Dict Notation
```yaml
body:
  - text: "Simple text"           # text widget with label="Simple text"
  - button:
      label: "Click"              # button with explicit params
```

## Data Binding

### Static vs Dynamic Values

```yaml
# Static (hardcoded)
text: "Hello World"

# Dynamic (from data tree)
data-id: my-node
text:                             # label comes from my-node/label
```

### data-id

Links a widget to a data path:

```yaml
- data-id: user-name
  text:                           # Reads label from current-path/user-name/label
```

### Data References with `@`

Reference values from data trees using `@` syntax:

```yaml
# Relative path (from current data context)
label: "@selection"
label: "@child/label"

# Absolute path (from tree root)
label: "@/root/selection"

# Parent-relative path
label: "@../sibling/label"

# Named tree reference with $tree@path
label: "$kernel@/audio/sample-rate"
selection: "$local@current-selection"
```

**Reference Syntax:**

| Pattern | Meaning |
|---------|---------|
| `"@path"` | Relative path in main data tree |
| `"@/abs/path"` | Absolute path in main tree |
| `"@../path"` | Parent-relative path |
| `"$tree@path"` | Path in named tree (e.g., `$kernel`, `$local`) |

**Note:** Values containing `@` must be quoted in YAML.

### Local Data Tree

Define widget-local data using `local`. This creates a DataTree scoped to the widget:

```yaml
my-popup:
  type: popup
  local:
    metadata:
      label: "New Item"
      count: 0
    children:
      options:
        metadata:
          selected: false
  body:
    - input-text:
        label: "$local@label"
    - text: "$local@count"
```

**Local tree features:**
- Follows standard DataTree structure (`metadata`/`children`)
- Accessed via `$local@path`
- Inherited by child widgets
- Read-write (widgets can modify local state)
- Context is root, so `$local@label` equals `$local@/label`

## Iteration

### foreach-child

Iterates over children of the current data node:

```yaml
data-id: items-list
body:
  foreach-child:
    - text                        # Creates text widget for each child
```

### foreach-key

Iterates over metadata keys:

```yaml
body:
  foreach-key:
    - text: "$key: $value"        # $key and $value are substituted
```

## Styling

### Style Colors

Apply ImGui colors using RGBA arrays:

```yaml
style:
  text: [1.0, 0.0, 0.0, 1.0]           # Red text
  button: [0.2, 0.6, 1.0, 1.0]         # Blue button
  button-hovered: [0.3, 0.7, 1.0, 1.0]
  button-active: [0.1, 0.5, 0.9, 1.0]
  frame-bg: [0.1, 0.1, 0.1, 1.0]
  border: [1.0, 1.0, 1.0, 1.0]
```

Common color names (kebab-case, converted to `imgui.Col_.*`):
- `text`, `text-disabled`
- `button`, `button-hovered`, `button-active`
- `frame-bg`, `frame-bg-hovered`, `frame-bg-active`
- `header`, `header-hovered`, `header-active`
- `border`, `border-shadow`
- `child-bg`, `popup-bg`, `window-bg`

### Style Variables

Apply ImGui style variables:

```yaml
style:
  frame-padding: [8, 4]           # Vec2
  frame-rounding: 4               # Float
  item-spacing: [8, 4]
```

### Conditional Styling

Apply styles based on metadata conditions:

```yaml
style-mapping:
  - when:
      selected: true
    style:
      text: [0.2, 1.0, 0.2, 1.0]
  - when:
      error: true
    style:
      text: [1.0, 0.2, 0.2, 1.0]
```

## Events

### Event Types

| Event | Trigger |
|-------|---------|
| `on-click` | Left mouse click |
| `on-right-click` | Right mouse click |
| `on-double-click` | Double click |
| `on-hover` | Mouse hover |
| `on-active` | Widget activated (e.g., tree node expanded) |
| `on-error` | Error occurred |

### Event Actions

#### show - Display a Widget
```yaml
on-click:
  show:
    popup:
      body:
        - text: "Popup content"
```

#### default - Default Action
```yaml
on-click: default              # Sets selection to current path
```

#### add-data-child - Add Data Node
```yaml
on-click:
  add-data-child:
    name: "new-item"
    metadata:
      label: "New Item"
```

#### dispatch-event - Send Event
```yaml
on-click:
  dispatch-event:
    name: "custom-event"
    data: { key: "value" }
```

### Conditional Events

```yaml
on-click:
  when:
    selected: true
  show:
    popup:
      body:
        - text: "Selected item clicked"
```

## Complete Example

```yaml
import:
  - components

widgets:
  main-window:
    type: imgui-main-window
    window-title: "My App"
    window-size: [800, 600]
    body:
      - text: "Welcome"
      - separator
      - button:
          label: "Show Items"
          body: app.items-popup
      - data-id: items
        collapsing-header:
          label: "Items List"
          body:
            foreach-child:
              - tree-node:
                  on-click: default
                  style-mapping:
                    - when: { selected: true }
                      style:
                        text: [0.2, 1.0, 0.2, 1.0]

  items-popup:
    type: popup
    body:
      - text: "Select an action"
      - separator
      - menu-item:
          label: "Add Item"
          on-click:
            add-data-child:
              name: "new-item"
              metadata:
                label: "New Item"

data:
  app-data:
    metadata:
      selection: null
    children:
      items:
        metadata:
          label: "Items"
        children:
          item1:
            metadata:
              label: "First Item"
          item2:
            metadata:
              label: "Second Item"

app:
  widget: app.main-window
  data: app-data
```

## Builtin Widgets

The `builtin` module provides utility widgets:

```yaml
# Tree view for hierarchical data
builtin.tree-view

# Error display with red styling
builtin.error-tree-view

# Use builtin collapsing header (fallback)
builtin.collapsing-header:
  label: "Section"
  body:
    - text: "Content"
```

## Child Widget Flags

The `child` widget supports ImGui child flags:

```yaml
child:
  border: true
  flags:
    - auto-resize-x
    - auto-resize-y
    - always-use-window-padding
  body:
    - text: "Content"
```

## Tips

1. **Use namespaces** - Organize widgets into modules for maintainability
2. **Prefer data binding** - Use `data-id` and `@` references over hardcoded values
3. **Use local state** - Use `local` for popup/form temporary state
4. **Leverage foreach** - Use `foreach-child` for dynamic lists
5. **Style sparingly** - Apply styles at the container level when possible
6. **Test incrementally** - Build UI piece by piece, testing each addition
