# Step 0: Minimal App

Welcome to Ymery! In this first step, we'll create the simplest possible application - just a window with some text.

## What You'll Learn

- The basic structure of a Ymery application
- How to define widgets in YAML
- How to run your first app

## The App Structure

Every Ymery application needs an `app.yaml` file with two main sections:

1. **`widgets:`** - Define your UI components
2. **`app:`** - Configure the application entry point

## The Code

```yaml
widgets:
  main-window:
    type: imgui-main-window
    label: "My First Ymery App"
    body:
      - text:
          label: "Hello, Ymery!"
      - separator:
      - text:
          label: "This is my first application."

app:
  widget: app.main-window
```

## Understanding the Code

### The `widgets:` Section

```yaml
widgets:
  main-window:           # Widget name (you choose this)
    type: imgui-main-window  # Widget type (built-in)
    label: "My First Ymery App"  # Window title
    body:                # Child widgets go here
      - text:
          label: "Hello, Ymery!"
```

- **`main-window`**: This is the name we give to our widget. We'll reference it later.
- **`type: imgui-main-window`**: This creates an ImGui window that serves as our application container.
- **`label`**: Sets the window title.
- **`body`**: A list of child widgets to display inside.

### The `app:` Section

```yaml
app:
  widget: app.main-window  # Which widget to use as the root
```

- **`widget: app.main-window`**: Tells Ymery to use the `main-window` widget from the `app` namespace (the current file) as the root of our application.

> **Note:** The `main-data` property is optional. If not specified, Ymery will automatically use the first defined data tree, or create an empty default if none exist.

### Widget Shortcuts

Notice how we define widgets in the body:

```yaml
body:
  - text:
      label: "Hello, Ymery!"
  - separator:            # Simple widget with no parameters
  - text:
      label: "Another line"
```

- **`text:`** with properties - Creates a text widget with the given label
- **`separator:`** alone - Some widgets need no configuration

## Running the App

```bash
./run.sh
```

Or manually:

```bash
uv run ymery --layouts-path . --main app
```

## What's Next?

In the next step, we'll add more interactive widgets like buttons and checkboxes!

---

[Next: Step 1 - Basic Widgets →](../01-basic-widgets/README.md)
