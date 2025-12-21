# Step 2: Data Binding

In the previous steps, our widgets looked nice but didn't store any values. Now we'll learn how to connect widgets to **data trees** - Ymery's way of managing application state.

## What You'll Learn

- How to define data trees
- How to bind widgets to data using `data-path`
- The `@` reference syntax for reading data
- How to display hierarchical data with `tree-view`

## Understanding Data Trees

A **data tree** is a hierarchical structure where each node has:
- **metadata**: Key-value pairs (like `label`, `value`, custom properties)
- **children**: Child nodes (optional)

```yaml
data:
  my-data:
    type: data-tree
    arg:
      metadata:
        label: "Root Node"
        description: "This is the root"
      children:
        child1:
          metadata:
            label: "First Child"
        child2:
          metadata:
            label: "Second Child"
```

## The Code

```yaml
data:
  # Define our application data tree
  app-data:
    type: data-tree
    arg:
      metadata:
        label: "Application Settings"
      children:
        user:
          metadata:
            label: "User Settings"
            name: "John Doe"
            age: 25
        display:
          metadata:
            label: "Display Settings"
            brightness: 0.8
            theme: "dark"
        audio:
          metadata:
            label: "Audio Settings"
            volume: 75
            muted: false

widgets:
  main-window:
    type: imgui-main-window
    label: "Data Binding Demo"
    body:
      - text:
          label: "Data Binding Demo"

      - separator:

      # Tree view shows the data structure
      - collapsing-header:
          label: "Data Tree View"
          flags: [default-open]
          body:
            - data-path: $app-data
              builtin.tree-view:

      # Bound widgets
      - collapsing-header:
          label: "Bound Widgets"
          flags: [default-open]
          body:
            - data-path: $app-data@/user
              body:
                - input-text:
                    label: "Name"
                    value: "@name"
                - slider-int:
                    label: "Age"
                    value: "@age"
                    min: 0
                    max: 120

            - separator-text:
                label: "Display"

            - data-path: $app-data@/display
              body:
                - slider-float:
                    label: "Brightness"
                    value: "@brightness"
                    min: 0.0
                    max: 1.0
                - combo:
                    label: "Theme"
                    value: "@theme"
                    items: ["light", "dark", "auto"]

            - separator-text:
                label: "Audio"

            - data-path: $app-data@/audio
              body:
                - slider-int:
                    label: "Volume"
                    value: "@volume"
                    min: 0
                    max: 100
                - checkbox:
                    label: "Muted"
                    value: "@muted"

app:
  widget: app.main-window
  main-data: app-data
```

## Key Concepts

### 1. Defining Data Trees

```yaml
data:
  app-data:              # Name of this data tree
    type: data-tree      # Type (data-tree is the default)
    arg:                 # The actual tree structure
      metadata:          # Key-value pairs for this node
        label: "Root"
      children:          # Child nodes
        child1:
          metadata:
            label: "Child"
```

### 2. Referencing Data Trees

Use `$tree-name` to reference a named data tree:

```yaml
- data-path: $app-data           # Reference the whole tree
- data-path: $app-data@/user     # Reference a specific path
```

### 3. The `@` Reference Syntax

The `@` symbol reads values from the current data context:

```yaml
# Relative reference (from current data-path)
label: "@name"           # Gets the "name" metadata key

# Absolute reference (from tree root)
label: "@/user/name"     # Gets name from /user path

# Parent reference
label: "@../sibling/value"  # Go up, then into sibling
```

### 4. Data Path Scope

`data-path` sets the data context for child widgets:

```yaml
- data-path: $app-data@/user    # Set context to /user
  body:
    - input-text:
        label: "Name"
        value: "@name"          # Reads from /user/name
    - input-text:
        label: "Email"
        value: "@email"         # Reads from /user/email
```

### 5. The Built-in Tree View

Ymery includes a tree view widget that displays any data tree:

```yaml
- data-path: $my-data
  builtin.tree-view:            # Shows expandable tree
```

## Setting the Main Data

In the `app:` section, you can optionally set a default data tree:

```yaml
app:
  widget: app.main-window
  main-data: app-data    # Sets $app-data as the default context
```

When `main-data` is set, widgets without explicit `data-path` use this tree.

> **Note:** If `main-data` is not specified, Ymery automatically uses the first defined data tree. This means for simple apps with one data tree, you can omit `main-data` entirely!

## Running the App

```bash
./run.sh
```

Try:
1. Expand the tree view to see all nodes
2. Modify values in the "Bound Widgets" section
3. Watch the tree view update in real-time!

## Exercises

1. Add a new child node called "network" with properties like "wifi-enabled" and "ssid"
2. Create bound widgets for your new network settings
3. Try using absolute references (`@/path/to/value`) instead of relative ones

## What's Next?

Our data is static - defined once at startup. In the next step, we'll learn how to **dynamically modify data** by adding children through events!

---

[← Previous: Step 1 - Basic Widgets](../01-basic-widgets/README.md) | [Next: Step 3 - Dynamic Data →](../03-dynamic-data/README.md)
