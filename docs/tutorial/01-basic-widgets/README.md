# Step 1: Basic Widgets

Now that you've created your first app, let's explore the variety of widgets Ymery offers!

## What You'll Learn

- How to use buttons, checkboxes, and input widgets
- How to organize widgets with collapsing headers
- How to add tooltips to widgets
- Widget styling basics

## Building on Step 0

We'll expand our simple app to include interactive widgets organized into sections.

## The Code

```yaml
widgets:
  main-window:
    type: imgui-main-window
    label: "Widget Showcase"
    body:
      - text:
          label: "Welcome to the Widget Showcase!"
          tooltip: "This tooltip appears when you hover over the text."

      - separator:

      # Buttons Section
      - collapsing-header:
          label: "Buttons"
          flags: [default-open]
          body:
            - button:
                label: "Click Me!"
            - same-line:
            - button:
                label: "Me Too!"
            - button:
                label: "Wide Button"
                size: [200, 0]

      # Input Section
      - collapsing-header:
          label: "Inputs"
          body:
            - checkbox:
                label: "Enable Feature"
            - slider-int:
                label: "Volume"
                min: 0
                max: 100
            - input-text:
                label: "Your Name"

      # Selection Section
      - collapsing-header:
          label: "Selection"
          body:
            - combo:
                label: "Choose One"
                items: ["Option A", "Option B", "Option C"]
            - radio-button:
                label: "Small"
                group: size-group
            - radio-button:
                label: "Medium"
                group: size-group
            - radio-button:
                label: "Large"
                group: size-group

app:
  widget: app.main-window
```

## Widget Reference

### Text Display

```yaml
- text:
    label: "Static text"
    tooltip: "Hover text"  # Optional tooltip
```

### Buttons

```yaml
- button:
    label: "Click Me"
    size: [width, height]  # Optional, [0, 0] = auto-size
    tooltip: "Button description"
```

### Checkboxes

```yaml
- checkbox:
    label: "Enable something"
```

### Sliders

```yaml
- slider-int:
    label: "Integer Value"
    min: 0
    max: 100

- slider-float:
    label: "Float Value"
    min: 0.0
    max: 1.0
```

### Input Fields

```yaml
- input-text:
    label: "Enter text"

- input-int:
    label: "Enter number"
```

### Combo Boxes (Dropdowns)

```yaml
- combo:
    label: "Select"
    items: ["A", "B", "C"]
```

### Radio Buttons

```yaml
- radio-button:
    label: "Option 1"
    group: my-group  # All radios in same group are exclusive

- radio-button:
    label: "Option 2"
    group: my-group
```

## Layout Widgets

### Collapsing Header

Groups widgets into a collapsible section:

```yaml
- collapsing-header:
    label: "Section Title"
    flags: [default-open]  # Optional: start expanded
    body:
      - text:
          label: "Content inside"
```

### Same Line

Places the next widget on the same line:

```yaml
- button:
    label: "First"
- same-line:
- button:
    label: "Second"  # Appears next to "First"
```

### Separator

Adds a horizontal line:

```yaml
- separator:
```

### Separator with Text

```yaml
- separator-text:
    label: "Section Name"
```

## Tooltips

Any widget can have a tooltip:

```yaml
- button:
    label: "Hover me"
    tooltip: "This appears on hover!"
```

## Running the App

```bash
./run.sh
```

## Exercises

1. Add a `slider-float` for brightness (0.0 to 1.0)
2. Create a new collapsing header for "Settings"
3. Add tooltips to all the buttons
4. Try the `color-edit` widget for picking colors

## What's Next?

These widgets look nice, but they don't actually *do* anything yet! In the next step, we'll learn about **data binding** - connecting widgets to data so they can read and store values.

---

[← Previous: Step 0 - Minimal App](../00-minimal-app/README.md) | [Next: Step 2 - Data Binding →](../02-data-binding/README.md)
