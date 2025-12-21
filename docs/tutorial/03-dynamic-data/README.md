# Step 3: Dynamic Data with Events

So far our data has been static - defined at startup and never changing in structure. Now we'll learn how to **dynamically add and modify data** through user interactions!

## What You'll Learn

- How to handle click events with `on-click`
- How to add children to data trees dynamically
- How to iterate over children with `foreach-child`
- Selection handling with events

## Event Handling Basics

Ymery supports several event types:

| Event | Trigger |
|-------|---------|
| `on-click` | Left mouse button click |
| `on-right-click` | Right mouse button click |
| `on-double-click` | Double click |
| `on-hover` | Mouse hovering over widget |
| `on-active` | Widget activated (e.g., tree node expanded) |

## The Code

```yaml
data:
  todo-list:
    type: data-tree
    arg:
      metadata:
        label: "My Todo List"
        next-id: 3
      children:
        item-1:
          metadata:
            label: "Learn Ymery basics"
            done: true
        item-2:
          metadata:
            label: "Build my first app"
            done: false

widgets:
  # Reusable todo item widget
  todo-item:
    type: composite
    body:
      - checkbox:
          label: "@label"
          value: "@done"

  # Main window
  main-window:
    type: imgui-main-window
    label: "Todo App"
    body:
      - text:
          label: "Todo List"

      - separator:

      # Add new todo button
      - button:
          label: "Add Todo"
          event-handlers:
            on-click:
              add-data-child:
                name: "item-$next-id"
                metadata:
                  label: "New todo item"
                  done: false
                increment:
                  next-id: 1

      - separator:

      # Display all todos using foreach-child
      - data-path: $todo-list
        body:
          foreach-child:
            - app.todo-item:

app:
  widget: app.main-window
  main-data: todo-list
```

## Key Concepts

### 1. Event Handlers Block

Events are defined in the `event-handlers:` block:

```yaml
- button:
    label: "Click Me"
    event-handlers:
      on-click:
        # action here
      on-hover:
        # another action
```

### 2. Adding Data Children

The `add-data-child` action adds a new node to the current data path:

```yaml
event-handlers:
  on-click:
    add-data-child:
      name: "new-item"        # Child node name
      metadata:               # Initial metadata
        label: "New Item"
        value: 0
```

### 3. Dynamic Naming with Variables

Use `$variable` to insert metadata values into names:

```yaml
add-data-child:
  name: "item-$next-id"    # Uses the "next-id" metadata value
  increment:
    next-id: 1             # Increment after adding
```

### 4. Iterating with foreach-child

`foreach-child` creates a widget for each child of the current data node:

```yaml
- data-path: $my-list
  body:
    foreach-child:
      - text:
          label: "@label"    # Each child's label
```

The data context automatically changes for each child, so `@label` refers to that child's label.

### 5. Selection Handling

Use `on-click: default` for selection behavior:

```yaml
- selectable:
    label: "@label"
    event-handlers:
      on-click: default    # Sets this node as selected
```

## Complete Todo App Example

```yaml
data:
  todo-list:
    type: data-tree
    arg:
      metadata:
        label: "My Todos"
        next-id: 1
        selection: ""
      children: {}

widgets:
  todo-item:
    type: composite
    body:
      - group:
          body:
            - checkbox:
                label: ""
                value: "@done"
            - same-line:
            - selectable:
                label: "@label"
                selection: "$todo-list@/selection"
                event-handlers:
                  on-click: default

  main-window:
    type: imgui-main-window
    label: "Dynamic Todo App"
    body:
      - text:
          label: "My Todo List"

      - separator:

      # Input for new todo
      - input-text:
          label: "New Todo"
          value: "$todo-list@/new-todo-text"

      - same-line:

      - button:
          label: "Add"
          event-handlers:
            on-click:
              add-data-child:
                name: "todo-$next-id"
                metadata:
                  label: "$new-todo-text"
                  done: false
                increment:
                  next-id: 1

      - separator:

      # List all todos
      - data-path: $todo-list
        body:
          foreach-child:
            - app.todo-item:

      - separator:

      # Show selection
      - text:
          label: "Selected:"
      - data-path: $todo-list
        text:
          label: "@selection"

app:
  widget: app.main-window
  main-data: todo-list
```

## Running the App

```bash
./run.sh
```

Try:
1. Click "Add Todo" multiple times - watch new items appear!
2. Check/uncheck the todo items
3. Click on items to select them

## Event Actions Reference

| Action | Description |
|--------|-------------|
| `add-data-child` | Add a child node to current data path |
| `default` | Default behavior (usually sets selection) |
| `show` | Show a popup or tooltip |
| `dispatch-event` | Dispatch a custom event |

## Exercises

1. Add a "Delete" button that removes the selected todo
2. Add a counter showing "X of Y completed"
3. Style completed todos differently (hint: use `style-mapping`)
4. Add a "Clear Completed" button

## What's Next?

Now that we can handle events, let's learn about **popups and tooltips** - widgets that appear on demand!

---

[← Previous: Step 2 - Data Binding](../02-data-binding/README.md) | [Next: Step 4 - Popups and Tooltips →](../04-popups-and-tooltips/README.md)
