# Ymery Tutorial

Welcome to the Ymery tutorial! This step-by-step guide will teach you how to build interactive GUI applications using Ymery's declarative YAML-based approach.

## What is Ymery?

Ymery is a framework for building GUI applications using:
- **YAML** for declarative UI definitions
- **Dear ImGui** for high-performance rendering
- **Python** for logic and data providers

No GUI code required - just describe your interface in YAML!

## Prerequisites

- Python 3.10+
- uv package manager
- ymery installed (`uv pip install ymery` or from source)

## Tutorial Steps

| Step | Topic | Description |
|------|-------|-------------|
| [Step 0](./00-minimal-app/README.md) | **Minimal App** | Your first Ymery application |
| [Step 1](./01-basic-widgets/README.md) | **Basic Widgets** | Buttons, inputs, sliders, and more |
| [Step 2](./02-data-binding/README.md) | **Data Binding** | Connect widgets to data trees |
| [Step 3](./03-dynamic-data/README.md) | **Dynamic Data** | Add/modify data with events |
| [Step 4](./04-popups-and-tooltips/README.md) | **Popups & Tooltips** | Rich tooltips and popup dialogs |
| [Step 5](./05-hello-imgui-docking/README.md) | **HelloImGui Docking** | Professional dockable window layouts |
| [Step 6](./06-modular-structure/README.md) | **Modular Structure** | Organize code across files |
| [Step 7](./07-advanced-custom-treelike/README.md) | **Advanced: Custom TreeLike** | Create custom data providers |

## Quick Start

Each tutorial step includes:
- `README.md` - Explanation and concepts
- `app.yaml` - The application code
- `run.sh` - Script to run the demo

To run any step:

```bash
cd docs/tutorial/00-minimal-app
./run.sh
```

Or manually:

```bash
uv run ymery --layouts-path docs/tutorial/00-minimal-app --main app
```

## What You'll Learn

### Core Concepts
- YAML-based widget definitions
- Widget types and properties
- Layout and composition

### Data Management
- Data trees and hierarchies
- The `@` reference syntax
- Data binding with `data-path`

### Interactivity
- Event handling (`on-click`, `on-hover`, etc.)
- Dynamic data manipulation
- Popups and modals

### Advanced Features
- HelloImGui docking system
- Application menus
- Modular project organization
- Custom data providers

## Project Structure

```
docs/tutorial/
├── README.md                          # This file
├── 00-minimal-app/
│   ├── README.md
│   ├── app.yaml
│   └── run.sh
├── 01-basic-widgets/
│   ├── README.md
│   ├── app.yaml
│   └── run.sh
├── 02-data-binding/
│   ├── README.md
│   ├── app.yaml
│   └── run.sh
├── 03-dynamic-data/
│   ├── README.md
│   ├── app.yaml
│   └── run.sh
├── 04-popups-and-tooltips/
│   ├── README.md
│   ├── app.yaml
│   └── run.sh
├── 05-hello-imgui-docking/
│   ├── README.md
│   ├── app.yaml
│   └── run.sh
├── 06-modular-structure/
│   ├── README.md
│   ├── app.yaml
│   ├── data.yaml
│   ├── widgets/
│   │   ├── explorer.yaml
│   │   ├── editor.yaml
│   │   ├── console.yaml
│   │   └── properties.yaml
│   └── run.sh
└── 07-advanced-custom-treelike/
    ├── README.md
    ├── app.yaml
    ├── plugins/
    │   ├── __init__.py
    │   └── system_monitor.py
    └── run.sh
```

## Key Concepts Quick Reference

### Widget Definition

```yaml
widgets:
  my-widget:
    type: composite        # Widget type
    body:                  # Child widgets
      - text:
          label: "Hello"
      - button:
          label: "Click"
```

### Data Binding

```yaml
data:
  my-data:
    type: data-tree
    arg:
      metadata:
        value: 42

widgets:
  display:
    type: text
    data-path: $my-data
    label: "@value"        # Reads from data
```

> **Tip:** `main-data` is optional in the `app:` section. Ymery automatically uses the first defined data tree if not specified.

### Events

```yaml
- button:
    label: "Click Me"
    event-handlers:
      on-click:
        add-data-child:
          name: "new-item"
          metadata:
            label: "New"
```

### Imports

```yaml
import:
  - widgets.buttons       # imports widgets/buttons.yaml
  - data                  # imports data.yaml
```

## Getting Help

- Check the demo applications in `demo/`
- Read the source code in `src/ymery/`
- Look at existing widget implementations in `src/ymery/plugins/frontend/`

## Next Steps

After completing this tutorial:

1. **Explore the demos** - See `demo/classic/` and `demo/hello-imgui-full/` for comprehensive examples
2. **Build your own app** - Start with Step 0 and customize
3. **Create custom providers** - Connect to your own data sources
4. **Contribute** - Help improve Ymery!

---

**Ready to begin?** → [Start with Step 0: Minimal App](./00-minimal-app/README.md)
