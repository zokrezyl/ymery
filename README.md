# Ymery

<p align="center">
  <img src="docs/logo.jpeg" alt="Ymery Logo" width="200">
</p>

**Build interactive GUI applications with YAML instead of code.**

Ymery lets you create [Dear ImGui](https://github.com/ocornut/imgui) applications using declarative YAML files, powered by [Dear ImGui Bundle](https://github.com/pthom/imgui_bundle) for Python.

## Why Ymery?

Traditional GUI development with ImGui requires writing repetitive boilerplate code. Every button, slider, or layout change means modifying and recompiling your application.

### Origins

Ymery emerged from building an audio viewing and analysis tool with imgui-bundle. We discovered that live data observation and manipulation was a central pattern - UI components constantly consuming and updating data in real-time. This led us to separate concerns in an MVC-like direction: the UI as a tree structure consuming an equivalent data tree, similar to React's approach in the web world.

While most UI elements directly manipulate or observe data tree nodes, the framework also supports event generation and handling. We're also exploring a broader vision: an "Ymery browser" where you write interactive applications with Python and YAML instead of HTML and JavaScript.

These concepts are in early alpha. **We'd love to hear your thoughts and suggestions.**

For architectural details, see [docs/design/main.md](docs/design/main.md).

**Ymery changes this:**
- **Declarative** - Define your UI in YAML, not code
- **Rapid iteration** - Edit layouts without recompiling
- **No programming required** - Create simple UIs with just YAML
- **Modular** - Reusable widget definitions with imports
- **Data-driven** - Separate UI structure from application logic

## Quick Example

Create a simple GUI in `app.yaml`:

```yaml
app:
  window_title: "Hello Ymery"
  widget: builtin.text
  data: greeting

data:
  greeting:
    metadata:
      label: "Welcome to Ymery!"
```

Run it:

```bash
ymery --main app
```

That's it. No Python code, no compilation - just a YAML file describing what you want.

## Who is Ymery for?

- **Python developers** who prefer declarative approaches
- **ImGui users** frustrated with boilerplate code
- **Data scientists** needing quick interactive tools
- **Game developers** prototyping UI and tools
- **Anyone** who wants to experiment with ImGui without writing code

## Framework or Library?

Both. Ymery provides structure and patterns (like a framework) but you can use it flexibly, picking what you need (like a library). Use it however it serves you best.

## Project Status

⚠️ **Early Alpha** - Ymery is experimental. APIs will change, features are incomplete, and breaking changes should be expected. We welcome feedback and contributions!

## Installation

```bash
pip install ymery
```

Requires Python 3.12+

## Examples

Check out the [demo](demo/) directory for examples:
- `demo/classic/` - Classic ImGui demo widgets
- `demo/hello-imgui/` - Basic Hello ImGui examples
- `demo/hello-imgui-full/` - Full-featured application layout

Run any demo:

```bash
ymery --layouts-path demo/hello-imgui-full --main app
```

## Documentation

- [Ymery Lang Reference](docs/ymery-lang.md) - YAML syntax and widget reference
- [Design Overview](docs/design/main.md) - Architecture and design patterns

For more examples, explore the YAML files in the demo directories.

## How It Works

1. **Write YAML** - Define your UI structure, widgets, and data
2. **Import modules** - Compose UIs from reusable components
3. **Run** - Ymery renders your YAML as a native ImGui application
4. **Iterate** - Change the YAML and see updates immediately

## Contributing

We're in early development and actively seeking feedback:
- Try Ymery with your use cases
- Report issues and suggest features
- Share what works and what doesn't

Your input helps shape Ymery's direction.

## License

[Add license information]

## Credits

Built on top of:
- [Dear ImGui](https://github.com/ocornut/imgui) by Omar Cornut
- [Dear ImGui Bundle](https://github.com/pthom/imgui_bundle) by Pascal Thomet
- [HelloImGui](https://github.com/pthom/hello_imgui) by Pascal Thomet
