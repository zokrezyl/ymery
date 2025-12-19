"""Hatch build hook to aggregate demo YAML files before building wheel."""
import json
import yaml
from pathlib import Path
from typing import Any
from hatchling.builders.hooks.plugin.interface import BuildHookInterface


def dir_name_to_label(name: str) -> str:
    """Convert directory name to human-readable label."""
    return ' '.join(word.capitalize() if word != 'imgui' else 'ImGui'
                    for word in name.replace('-', ' ').split())


class YAMLAggregator:
    """Aggregates YAML files from a demo directory into a single file"""

    def __init__(self, demo_dir: Path, search_paths: list[Path] = None):
        self.demo_dir = demo_dir
        self.search_paths = search_paths or [demo_dir]
        self.widgets = {}  # Merged widgets
        self.data = {}  # Merged data
        self.app_config = None  # App configuration
        self.visited_modules = set()  # Track visited modules to avoid cycles

    def find_yaml_file(self, module_name: str) -> Path | None:
        """Find a YAML file in search paths"""
        module_path = module_name.replace('.', '/')
        yaml_filename = f"{module_path}.yaml"

        for search_path in self.search_paths:
            candidate = search_path / yaml_filename
            if candidate.exists():
                return candidate
        return None

    def load_yaml(self, file_path: Path) -> dict:
        """Load YAML file"""
        try:
            with open(file_path, 'r') as f:
                content = yaml.safe_load(f)
                return content or {}
        except Exception as e:
            print(f"  Warning: Error loading {file_path}: {e}")
            return {}

    def process_module(self, module_name: str):
        """Process a module and its imports recursively"""
        if module_name in self.visited_modules:
            return

        self.visited_modules.add(module_name)

        # Find and load module
        module_file = self.find_yaml_file(module_name)
        if not module_file:
            print(f"  Warning: Module '{module_name}' not found")
            return

        module_content = self.load_yaml(module_file)

        # Process imports first (depth-first)
        imports = module_content.get('import', [])
        if isinstance(imports, str):
            imports = [imports]
        for imported_module in imports:
            self.process_module(imported_module)

        # Merge widgets WITHOUT namespace in widget name, but track the module
        widgets = module_content.get('widgets', {})
        for widget_name, widget_def in widgets.items():
            if widget_name in self.widgets:
                print(f"  Warning: Duplicate widget '{widget_name}' from '{module_name}', overwriting")
            self.widgets[widget_name] = (module_name, widget_def)

        # Merge data
        data = module_content.get('data', {})
        for data_name, data_def in data.items():
            if data_name in self.data:
                print(f"  Warning: Duplicate data '{data_name}', overwriting")
            self.data[data_name] = data_def

        # Capture app config from any module (last one wins)
        if 'app' in module_content:
            self.app_config = module_content['app']

    def strip_module_prefix(self, ref: str) -> str:
        """
        Strip module prefix from a widget reference if it matches a known widget.

        E.g., "widgets.kernel-demo-popup" -> "kernel-demo-popup"
        E.g., "widgets.basic.basic-demo" -> "basic-demo"
        E.g., "app.main-window" -> "main-window"
        """
        if '.' not in ref:
            return ref

        # Try progressively stripping prefixes until we find a match
        parts = ref.split('.')
        for i in range(1, len(parts)):
            widget_name = '.'.join(parts[i:])
            if widget_name in self.widgets:
                return widget_name

        return ref

    def process_widget_references(self, obj: Any) -> Any:
        """
        Recursively process widget references in the structure.

        Strips module prefixes from widget references to match the
        aggregated widget declarations (which have no namespace).
        """
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                # Widget references can appear as dict keys (e.g., "widgets.basic.demo: null")
                new_key = self.strip_module_prefix(key)
                # Check keys that typically contain widget references
                if key in ('body', 'type', 'widget') and isinstance(value, str):
                    result[new_key] = self.strip_module_prefix(value)
                else:
                    result[new_key] = self.process_widget_references(value)
            return result
        elif isinstance(obj, list):
            return [self.process_widget_references(item) for item in obj]
        elif isinstance(obj, str):
            # String values in lists might be widget references
            return self.strip_module_prefix(obj)
        else:
            return obj

    def aggregate(self, main_module: str) -> dict:
        """Aggregate all YAML files starting from main module"""
        # Process main module and all its dependencies
        self.process_module(main_module)

        # Build final structure
        result = {}

        # Add app config if present
        if self.app_config:
            result['app'] = self.process_widget_references(self.app_config)

        # Add all widgets
        if self.widgets:
            result['widgets'] = {}
            for widget_name, (module_name, widget_def) in self.widgets.items():
                result['widgets'][widget_name] = self.process_widget_references(widget_def)

        # Add all data
        if self.data:
            result['data'] = {}
            for data_name, data_def in self.data.items():
                result['data'][data_name] = self.process_widget_references(data_def)

        return result

    def save(self, output_file: Path, content: dict):
        """Save aggregated YAML to file"""
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w') as f:
            # Add header comment
            f.write(f"# Aggregated YAML demo for browser (Pyodide)\n")
            f.write(f"# Source: {self.demo_dir}\n")
            f.write(f"# Feel free to edit and experiment!\n\n")

            yaml.dump(content, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


class CustomBuildHook(BuildHookInterface):
    """Build hook that aggregates YAML demo files."""

    def initialize(self, version, build_data):
        """Run before building the wheel."""
        if self.target_name != "wheel":
            return

        print("Running YAML aggregation before wheel build...")

        # Create aggregated demo directory
        aggregated_dir = Path("demo-aggregated")
        aggregated_dir.mkdir(exist_ok=True)

        # Create __init__.py so it's recognized as a Python package
        init_file = aggregated_dir / "__init__.py"
        init_file.write_text('"""Aggregated demo YAML files."""\n')

        # Find all demo directories
        demo_base = Path("demo")
        if not demo_base.exists():
            print("  Warning: demo/ directory not found, skipping aggregation")
            return

        aggregated_count = 0
        examples = []

        # Find all demo directories (sorted for consistent ordering)
        demo_dirs = sorted([
            d for d in demo_base.iterdir()
            if d.is_dir() and not d.name.startswith('.') and d.name != "old-and-obsolete" and (d / "app.yaml").exists()
        ])

        # Aggregate each demo subdirectory
        for demo_dir in demo_dirs:
            output_file = aggregated_dir / f"{demo_dir.name}.yaml"
            print(f"  Aggregating {demo_dir.name} -> {output_file.name}")

            try:
                aggregator = YAMLAggregator(demo_dir, search_paths=[demo_dir])
                aggregated = aggregator.aggregate("app")
                aggregator.save(output_file, aggregated)
                aggregated_count += 1

                # Add to examples list
                examples.append({
                    "label": dir_name_to_label(demo_dir.name),
                    "aggregated_file": f"{demo_dir.name}.yaml",
                    "description": f"{dir_name_to_label(demo_dir.name)} demo"
                })
            except Exception as e:
                print(f"  Error aggregating {demo_dir.name}: {e}")
                # Continue with other demos even if one fails

        # Write examples.json
        examples_json_path = aggregated_dir / "examples.json"
        with open(examples_json_path, 'w') as f:
            json.dump({"examples": examples}, f, indent=2)
            f.write('\n')

        print(f"Successfully aggregated {aggregated_count} demo files")
        print(f"Generated {examples_json_path} with {len(examples)} examples")
