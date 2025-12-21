# Step 6: Modular YAML Structure

As applications grow, a single YAML file becomes unwieldy. Ymery's **import system** lets you split your code into multiple files for better organization!

## What You'll Learn

- How to split widgets into separate files
- How to split data definitions
- How namespacing works
- Best practices for project organization

## Project Structure

A well-organized Ymery project might look like:

```
my-app/
├── app.yaml           # Main entry point
├── data.yaml          # Data tree definitions
├── widgets/
│   ├── sidebar.yaml   # Sidebar widgets
│   ├── editor.yaml    # Editor widgets
│   └── toolbar.yaml   # Toolbar widgets
└── run.sh
```

## The Import System

Use `import:` to include other YAML files:

```yaml
# app.yaml
import:
  - data                    # imports data.yaml
  - widgets.sidebar         # imports widgets/sidebar.yaml
  - widgets.editor          # imports widgets/editor.yaml
```

## Namespacing

Each file creates a namespace based on its path:

| File | Namespace |
|------|-----------|
| `app.yaml` | `app` |
| `data.yaml` | `data` |
| `widgets/sidebar.yaml` | `widgets.sidebar` |
| `widgets/editor.yaml` | `widgets.editor` |

To use a widget from another file, use its full namespace:

```yaml
# In app.yaml, using widget from widgets/sidebar.yaml
body:
  - widgets.sidebar.file-tree:
```

## Example: Modular IDE

Let's refactor our IDE from Step 5 into multiple files:

### File: `app.yaml`

```yaml
import:
  - data
  - widgets.explorer
  - widgets.editor
  - widgets.console

widgets:
  main-window:
    type: hello-imgui-main-window
    runner-params:
      app-window-params:
        window-geometry:
          size: [1400, 900]
      imgui-window-params:
        default-imgui-window-type: provide-full-screen-dock-space
    body:
      # Docking layout
      - docking-split:
          initial-dock: "MainDockSpace"
          new-dock: "LeftPanel"
          direction: "left"
          ratio: 0.2

      - docking-split:
          initial-dock: "MainDockSpace"
          new-dock: "BottomPanel"
          direction: "down"
          ratio: 0.25

      # Use widgets from imported files
      - widgets.explorer.panel:
      - widgets.editor.panel:
      - widgets.console.panel:

app:
  widget: app.main-window
  main-data: app-data
```

### File: `data.yaml`

```yaml
data:
  app-data:
    type: data-tree
    arg:
      metadata:
        label: "App"
      children:
        files:
          metadata:
            label: "Files"
          children:
            main:
              metadata:
                label: "main.py"
            utils:
              metadata:
                label: "utils.py"
```

### File: `widgets/explorer.yaml`

```yaml
widgets:
  panel:
    type: dockable-window
    label: "Explorer"
    dock-space-name: "LeftPanel"
    tooltip: "Browse files"
    body:
      - explorer.file-tree:

  file-tree:
    type: composite
    body:
      - text:
          label: "Files"
      - separator:
      - data-path: $app-data@/files
        builtin.tree-view:
```

### File: `widgets/editor.yaml`

```yaml
widgets:
  panel:
    type: dockable-window
    label: "Editor"
    dock-space-name: "MainDockSpace"
    tooltip: "Edit files"
    body:
      - editor.content:

  content:
    type: composite
    body:
      - text:
          label: "Editor Content"
      - separator:
      - text:
          label: "Select a file to edit"
```

### File: `widgets/console.yaml`

```yaml
widgets:
  panel:
    type: dockable-window
    label: "Console"
    dock-space-name: "BottomPanel"
    tooltip: "View output"
    body:
      - console.output:

  output:
    type: composite
    body:
      - text:
          label: "> Ready"
```

## Namespace Resolution

When Ymery looks for a widget:

1. First checks the current file's namespace
2. Then checks imported namespaces
3. Finally checks built-in widgets

```yaml
# In widgets/explorer.yaml (namespace: widgets.explorer)

body:
  - file-tree:           # Looks for widgets.explorer.file-tree (found!)
  - editor.content:      # Looks for widgets.explorer.editor.content (not found)
                         # Then looks for widgets.editor.content (found!)
  - builtin.tree-view:   # Always available
```

## Sharing Data Across Files

Data trees defined in one file are available everywhere:

```yaml
# data.yaml
data:
  shared-config:
    type: data-tree
    arg:
      metadata:
        theme: "dark"

# widgets/settings.yaml (can access shared-config)
widgets:
  theme-picker:
    body:
      - data-path: $shared-config
        combo:
          label: "Theme"
          value: "@theme"
          items: ["light", "dark"]
```

## Best Practices

### 1. One Responsibility Per File

```
widgets/
├── navigation.yaml    # Navigation components
├── forms.yaml         # Form widgets
├── dialogs.yaml       # Dialog/modal widgets
└── charts.yaml        # Chart widgets
```

### 2. Group Related Data

```yaml
# data.yaml - all data in one place
data:
  user-data:
    # user-related data
  app-settings:
    # application settings
  cache:
    # cached data
```

### 3. Use Clear Naming

```yaml
# Good
widgets:
  user-profile-card:
  settings-panel:
  file-tree-view:

# Avoid
widgets:
  card1:
  panel:
  tree:
```

### 4. Keep app.yaml Minimal

The main `app.yaml` should focus on:
- Imports
- Main window structure
- Docking layout
- App configuration

## Running the App

```bash
./run.sh
```

## Exercises

1. Add a new file `widgets/toolbar.yaml` with a toolbar widget
2. Create `widgets/dialogs/` folder with `settings.yaml` and `about.yaml`
3. Split your data into `data/user.yaml` and `data/config.yaml`
4. Create reusable button styles in `widgets/common.yaml`

## What's Next?

In the final step, we'll go advanced - creating a **custom TreeLike data provider** to connect Ymery to external data sources!

---

[← Previous: Step 5 - Hello ImGui Docking](../05-hello-imgui-docking/README.md) | [Next: Step 7 - Advanced Custom TreeLike →](../07-advanced-custom-treelike/README.md)
