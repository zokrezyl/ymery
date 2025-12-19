# Build System

## Overview

Ymery uses **uv** for dependency management and **hatchling** as the build backend. The build process includes automatic YAML aggregation for browser demos.

## Project Configuration

### pyproject.toml

```toml
[build-system]
requires = ["hatchling", "pyyaml"]
build-backend = "hatchling.build"
```

Key sections:

- **build-system**: Uses hatchling with pyyaml (needed for aggregation hook)
- **project**: Package metadata, dependencies, Python version (>=3.12)
- **tool.hatch.build**: Custom build hooks and file inclusion rules

### Dependencies

Core runtime dependencies:
- `imgui-bundle` - Dear ImGui Python bindings
- `pyyaml` - YAML parsing
- `click` - CLI framework
- `munch` - Dictionary with attribute access
- `pillow` - Image handling
- `httpx` - HTTP client

All versions are constrained for Pyodide 0.29.0 compatibility.

## Building

### Commands

```bash
# Install dependencies
uv sync

# Build wheel and sdist
uv build

# Or via Makefile
make build
```

### Build Process

1. **uv build** invokes hatchling as the build backend
2. Hatchling runs the custom build hook (`scripts/hatch_build.py`)
3. The hook aggregates demo YAML files
4. Final wheel includes:
   - `ymery/` - Main package
   - `ymery/demo/` - Modular demo files
   - `ymery/demo_aggregated/` - Aggregated demos for browser

## YAML Aggregation

### Purpose

Demo applications are written as modular YAML files with imports. For browser demos (Pyodide), these must be aggregated into single standalone files.

### How It Works

The build hook in `scripts/hatch_build.py`:

1. Scans `demo/*/app.yaml` for demo directories
2. Recursively processes imports
3. Merges all widgets and data into a single file
4. Strips module namespace prefixes from widget references

Example transformation:
```yaml
# Before (modular)
import: widgets
app:
  widget: app.main-window
widgets:
  main-window:
    body: widgets.kernel-demo-popup

# After (aggregated)
app:
  widget: main-window
widgets:
  main-window:
    body: kernel-demo-popup
  kernel-demo-popup:
    ...
```

### Output

Aggregated files are written to `demo-aggregated/` during build and included in the wheel as `ymery/demo_aggregated/`.

## Publishing to PyPI

### Manual Release

```bash
# Build
make build

# Upload to PyPI
make upload
```

### Version Bumping

```bash
make bump-patch   # 0.0.X -> 0.0.X+1
make bump-minor   # 0.X.0 -> 0.X+1.0
make bump-major   # X.0.0 -> X+1.0.0
```

### Full Release

```bash
make release  # clean + build + upload
```

## Pyodide Browser Demo

### Architecture

```
Browser
├── JavaScript (docs/demo/js/)
│   ├── main.js           - Entry point
│   ├── pyodide_loader.js - Python environment setup
│   ├── examples.js       - Demo selector
│   └── ui.js             - Editor UI
├── Pyodide (Python WebAssembly)
│   ├── imgui_bundle      - From Pyodide 0.29.0
│   └── ymery             - From PyPI via micropip
└── WebGL Canvas          - ImGui rendering
```

### How It Works

1. Browser loads Pyodide from CDN
2. `pyodide_loader.js` installs ymery from PyPI via micropip
3. User selects a demo from dropdown
4. Aggregated YAML is fetched from `docs/demo/examples/aggregated/`
5. YAML is written to Pyodide virtual filesystem
6. Ymery runs with `--layouts-path /tmp/ymery_demo --main app`

### Updating Browser Demos

After publishing a new version to PyPI:

1. Copy aggregated files to docs:
   ```bash
   # Extract from wheel
   unzip -j dist/ymery-*.whl "ymery/demo_aggregated/*.yaml" -d docs/demo/examples/aggregated/
   ```

2. Update `docs/demo/examples/examples.json` if demos changed

3. Commit and push to main branch

4. GitHub Pages auto-deploys from `docs/` directory

### Cache Considerations

- PyPI CDN can take 5-10 minutes to propagate
- Browser caching may require hard refresh (Ctrl+Shift+R)
- Pyodide caches packages; users may need to clear browser data

## File Structure

```
/
├── pyproject.toml           # Package configuration
├── Makefile                 # Build commands
├── scripts/
│   ├── hatch_build.py       # Build hook (aggregation)
│   └── bump_version.py      # Version management
├── demo/                    # Modular demo sources
│   ├── classic/
│   ├── hello-imgui/
│   └── hello-imgui-full/
├── demo-aggregated/         # Generated during build (not in repo)
├── dist/                    # Build output
│   ├── ymery-X.X.X.tar.gz
│   └── ymery-X.X.X-py3-none-any.whl
└── docs/
    └── demo/                # Browser demo (GitHub Pages)
        ├── index.html
        ├── js/
        └── examples/
            └── aggregated/  # Aggregated YAMLs for browser
```
