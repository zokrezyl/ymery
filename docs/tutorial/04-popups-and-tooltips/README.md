# Step 4: Popups and Tooltips

Popups and tooltips are widgets that appear on demand - when the user clicks or hovers. They're perfect for additional information, confirmation dialogs, or context menus!

## What You'll Learn

- How to create rich tooltips with multiple widgets
- How to show popups on button clicks
- How to create modal dialogs
- Right-click context menus

## Simple vs Rich Tooltips

We've already seen simple tooltips:

```yaml
- button:
    label: "Hover me"
    tooltip: "Simple text tooltip"
```

But you can also create **rich tooltips** with multiple widgets!

## The Code

```yaml
widgets:
  main-window:
    type: imgui-main-window
    label: "Popups & Tooltips Demo"
    body:
      # ===========================================
      # Rich Tooltips
      # ===========================================
      - collapsing-header:
          label: "Rich Tooltips"
          flags: [default-open]
          body:
            - button:
                label: "Hover for Rich Tooltip"
                event-handlers:
                  on-hover:
                    show:
                      tooltip:
                        body:
                          - text:
                              label: "This is a rich tooltip!"
                          - separator:
                          - bullet-text:
                              label: "It can contain multiple widgets"
                          - bullet-text:
                              label: "Like bullet points"
                          - bullet-text:
                              label: "And more!"

      # ===========================================
      # Click Popups
      # ===========================================
      - collapsing-header:
          label: "Click Popups"
          flags: [default-open]
          body:
            - button:
                label: "Click for Popup"
                event-handlers:
                  on-click:
                    show:
                      popup:
                        body:
                          - text:
                              label: "Popup Content"
                          - separator:
                          - button:
                              label: "Close"

      # ===========================================
      # Modal Dialogs
      # ===========================================
      - collapsing-header:
          label: "Modal Dialogs"
          body:
            - button:
                label: "Open Modal"
                event-handlers:
                  on-click:
                    show:
                      popup-modal:
                        label: "Confirmation"
                        body:
                          - text:
                              label: "Are you sure?"
                          - separator:
                          - button:
                              label: "Yes"
                          - same-line:
                          - button:
                              label: "No"

      # ===========================================
      # Context Menus
      # ===========================================
      - collapsing-header:
          label: "Context Menus"
          body:
            - text:
                label: "Right-click here!"
                event-handlers:
                  on-right-click:
                    show:
                      popup:
                        body:
                          - menu-item:
                              label: "Copy"
                          - menu-item:
                              label: "Paste"
                          - separator:
                          - menu-item:
                              label: "Delete"

app:
  widget: app.main-window
```

## Key Concepts

### 1. Rich Tooltips

Use `on-hover` with `show: tooltip:` to create multi-widget tooltips:

```yaml
event-handlers:
  on-hover:
    show:
      tooltip:
        body:
          - text:
              label: "Title"
          - separator:
          - text:
              label: "Description here..."
```

### 2. Click Popups

Use `on-click` with `show: popup:` for click-triggered popups:

```yaml
event-handlers:
  on-click:
    show:
      popup:
        body:
          - text:
              label: "Popup content"
          - button:
              label: "Action"
```

### 3. Modal Dialogs

Modals block interaction with the rest of the UI until closed:

```yaml
event-handlers:
  on-click:
    show:
      popup-modal:
        label: "Dialog Title"
        body:
          - text:
              label: "Modal content"
```

### 4. Context Menus (Right-Click)

```yaml
event-handlers:
  on-right-click:
    show:
      popup:
        body:
          - menu-item:
              label: "Option 1"
          - menu-item:
              label: "Option 2"
```

## Popups with Data

Popups can also use data binding:

```yaml
- button:
    label: "Edit Settings"
    event-handlers:
      on-click:
        show:
          popup-modal:
            label: "Settings"
            body:
              - data-path: $app-data@/settings
                body:
                  - slider-int:
                      label: "Volume"
                      value: "@volume"
                  - checkbox:
                      label: "Enabled"
                      value: "@enabled"
```

## Popup Actions

Buttons inside popups can trigger actions too:

```yaml
popup-modal:
  label: "Add Item"
  body:
    - input-text:
        label: "Name"
        value: "@new-name"
    - button:
        label: "Add"
        event-handlers:
          on-click:
            add-data-child:
              name: "item-$next-id"
              metadata:
                label: "$new-name"
```

## Running the App

```bash
./run.sh
```

Try:
1. Hover over the tooltip button
2. Click the popup button
3. Open the modal dialog
4. Right-click on the context menu area

## Exercises

1. Create a "Delete Confirmation" modal that appears before deleting an item
2. Make a settings popup with multiple tabs
3. Create a rich tooltip that shows data from a data tree
4. Add a context menu to the todo items from Step 3

## What's Next?

Now that we've mastered basic ImGui, let's level up to **HelloImGui** with its powerful docking system!

---

[← Previous: Step 3 - Dynamic Data](../03-dynamic-data/README.md) | [Next: Step 5 - Hello ImGui Docking →](../05-hello-imgui-docking/README.md)
