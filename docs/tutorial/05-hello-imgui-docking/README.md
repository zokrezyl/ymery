# Step 5: Hello ImGui Docking

Time to level up! **HelloImGui** extends Dear ImGui with powerful features like docking, viewports, and application lifecycle management. The docking system lets users arrange windows freely!

## What You'll Learn

- How to create a HelloImGui application
- How to define docking layouts with splits
- How to create dockable windows
- How to add application menus

## HelloImGui vs ImGui

| Feature | `imgui-main-window` | `hello-imgui-main-window` |
|---------|---------------------|---------------------------|
| Basic widgets | Yes | Yes |
| Docking | No | Yes |
| Multiple viewports | No | Yes |
| Application menus | Manual | Built-in |
| Window management | No | Yes |

## The Code

```yaml
widgets:
  main-window:
    type: hello-imgui-main-window
    runner-params:
      app-window-params:
        window-geometry:
          size: [1200, 800]
      imgui-window-params:
        default-imgui-window-type: provide-full-screen-dock-space
    fps-idle: 0
    body:
      # Define dock layout
      - docking-split:
          initial-dock: "MainDockSpace"
          new-dock: "LeftPanel"
          direction: "left"
          ratio: 0.25

      - docking-split:
          initial-dock: "MainDockSpace"
          new-dock: "BottomPanel"
          direction: "down"
          ratio: 0.3

      # Create dockable windows
      - dockable-window:
          label: "Explorer"
          dock-space-name: "LeftPanel"
          body:
            - text:
                label: "File explorer here"

      - dockable-window:
          label: "Editor"
          dock-space-name: "MainDockSpace"
          body:
            - text:
                label: "Main editor content"

      - dockable-window:
          label: "Console"
          dock-space-name: "BottomPanel"
          body:
            - text:
                label: "Console output"

app:
  widget: app.main-window
```

## Key Concepts

### 1. HelloImGui Main Window

```yaml
main-window:
  type: hello-imgui-main-window
  runner-params:
    app-window-params:
      window-geometry:
        size: [1200, 800]        # Window size
    imgui-window-params:
      default-imgui-window-type: provide-full-screen-dock-space
  fps-idle: 0                    # FPS when idle (0 = unlimited)
```

### 2. Docking Splits

Splits divide a dock space into two regions:

```yaml
- docking-split:
    initial-dock: "MainDockSpace"  # Source dock space
    new-dock: "LeftPanel"          # New dock space name
    direction: "left"              # left, right, up, down
    ratio: 0.25                    # 0.0 to 1.0 (size ratio)
```

The split directions:
- `left` / `right` - Horizontal split
- `up` / `down` - Vertical split

### 3. Dockable Windows

Windows that can be docked, undocked, and rearranged:

```yaml
- dockable-window:
    label: "Window Title"          # Tab label
    dock-space-name: "LeftPanel"   # Initial dock location
    tooltip: "Hover tooltip"       # Tooltip on dock tab
    body:
      - text:
          label: "Window content"
```

### 4. Application Menus

HelloImGui provides built-in menu support:

```yaml
body:
  # Application menu bar
  - hello-imgui-menu:
      body:
        - menu:
            label: "File"
            body:
              - menu-item:
                  label: "New"
              - menu-item:
                  label: "Open"
              - separator:
              - menu-item:
                  label: "Exit"

        - menu:
            label: "Edit"
            body:
              - menu-item:
                  label: "Cut"
              - menu-item:
                  label: "Copy"
              - menu-item:
                  label: "Paste"
```

## Building an IDE-like Layout

```yaml
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
      # Menu bar
      - hello-imgui-menu:
          body:
            - menu:
                label: "File"
                body:
                  - menu-item:
                      label: "New File"
                  - menu-item:
                      label: "Open"
                  - separator:
                  - menu-item:
                      label: "Save"
                  - menu-item:
                      label: "Save As..."
                  - separator:
                  - menu-item:
                      label: "Exit"
            - menu:
                label: "View"
                body:
                  - menu-item:
                      label: "Explorer"
                  - menu-item:
                      label: "Console"
                  - menu-item:
                      label: "Properties"

      # Layout: Left panel
      - docking-split:
          initial-dock: "MainDockSpace"
          new-dock: "LeftPanel"
          direction: "left"
          ratio: 0.2

      # Layout: Right panel
      - docking-split:
          initial-dock: "MainDockSpace"
          new-dock: "RightPanel"
          direction: "right"
          ratio: 0.25

      # Layout: Bottom panel
      - docking-split:
          initial-dock: "MainDockSpace"
          new-dock: "BottomPanel"
          direction: "down"
          ratio: 0.25

      # Windows
      - dockable-window:
          label: "Explorer"
          dock-space-name: "LeftPanel"
          tooltip: "Browse files and folders"
          body:
            - text:
                label: "File tree here"

      - dockable-window:
          label: "Editor"
          dock-space-name: "MainDockSpace"
          tooltip: "Main editing area"
          body:
            - text:
                label: "Editor content"

      - dockable-window:
          label: "Properties"
          dock-space-name: "RightPanel"
          tooltip: "View and edit properties"
          body:
            - text:
                label: "Properties panel"

      - dockable-window:
          label: "Console"
          dock-space-name: "BottomPanel"
          tooltip: "View application output"
          body:
            - text:
                label: "Console output"

      - dockable-window:
          label: "Problems"
          dock-space-name: "BottomPanel"
          tooltip: "View errors and warnings"
          body:
            - text:
                label: "No problems detected"
```

## Running the App

```bash
./run.sh
```

Try:
1. Drag window tabs to rearrange them
2. Drag a tab outside to create a floating window
3. Drag a floating window back to dock it
4. Use the View menu to toggle windows

## Docking Tips

- Windows in the same dock space appear as tabs
- Drag tabs to reorder them
- Drag to dock space edges to split
- The layout persists between runs (saved in imgui.ini)

## Exercises

1. Add a "Debug" dockable window to the bottom panel
2. Create a tabbed editor area with multiple file tabs
3. Add tooltips to all the dockable windows
4. Create a "Tools" menu with additional options

## What's Next?

Our YAML file is getting big! In the next step, we'll learn how to **split our code into multiple files** for better organization.

---

[← Previous: Step 4 - Popups and Tooltips](../04-popups-and-tooltips/README.md) | [Next: Step 6 - Modular Structure →](../06-modular-structure/README.md)
