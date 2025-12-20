"""
Language module - handles YAML loading and module management for ymery layouts
"""

import yaml
import httpx
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Union
from collections import deque
from ymery.types import Object
from ymery.result import Result, Ok


class Lang(Object):
    """
    Manages YAML module loading and resolution

    Handles:
    - Loading YAML files from search paths (breadth-first)
    - Processing import statements
    - Namespacing widgets by filename
    - Merging data and app sections
    """

    def __init__(self, layouts_paths: List[Union[str, Path]], main: str = "app"):
        """
        Args:
            layouts_paths: List of directories or URLs to search for YAML modules
        """
        super().__init__()
        self._layouts_paths = layouts_paths
        self._main = main

    def init(self) -> Result[None]:
        # Add builtin layouts directory
        builtin_layouts_dir = Path(__file__).parent / "frontend" / "layouts"

        # Separate local paths and URLs
        self._local_paths = [builtin_layouts_dir]
        self._url_bases = []

        for item in self._layouts_paths:
            if isinstance(item, str) and (item.startswith('http://') or item.startswith('https://')):
                self._url_bases.append(item.rstrip('/'))
            else:
                self._local_paths.append(Path(item))

        # Create temp directory for downloaded YAML files
        self._temp_dir = Path(tempfile.mkdtemp(prefix='ymery_layouts_'))

        self._widget_definitions = {}  # full_name (namespace.widget) -> widget definition
        self._data_definitions = {}  # data_name -> data definition
        self._app_config = None  # app configuration
        self._http_client = httpx.Client(timeout=30.0)

        """Initialize Lang - verify local search paths exist"""
        for path in self._local_paths:
            if not path.exists():
                return Result.error(f"Search path does not exist: {path}")
            if not path.is_dir():
                return Result.error(f"Search path is not a directory: {path}")
        return self._load_main_module()

    def dispose(self) -> Result[None]:
        """Clean up resources"""
        self._http_client.close()
        # Clean up temp directory
        import shutil
        if self._temp_dir.exists():
            shutil.rmtree(self._temp_dir)
        return Ok(None)

    def _load_main_module(self) -> Result[None]:
        """
        Load the main module and all its dependencies (breadth-first)

        Args:
            module_name: Name of the main module (without .yaml extension)

        Returns:
            Result[None]: Ok on success, Error on failure
        """
        module_name = self._main
        queue = deque([module_name, "builtin"])
        visited = set()

        while queue:
            current_module = queue.popleft()

            if current_module in visited:
                continue

            visited.add(current_module)

            # Find module file - support directory-based namespaces
            # Convert dots to slashes: "widgets.buttons" → "widgets/buttons.yaml"
            module_file = None
            module_path = current_module.replace('.', '/')
            yaml_filename = f"{module_path}.yaml"

            # Try local paths first
            for layouts_path in self._local_paths:
                candidate = layouts_path / yaml_filename
                if candidate.exists():
                    module_file = candidate
                    break

            # Try URLs if not found locally
            if module_file is None:
                for url_base in self._url_bases:
                    try:
                        url = f"{url_base}/{yaml_filename}"
                        response = self._http_client.get(url)
                        if response.status_code == 200:
                            # Download and cache in temp directory
                            cached_file = self._temp_dir / yaml_filename
                            cached_file.parent.mkdir(parents=True, exist_ok=True)
                            cached_file.write_text(response.text)
                            module_file = cached_file
                            break
                    except (httpx.HTTPError, httpx.TimeoutException, OSError) as e:
                        # HTTP errors, timeouts, or file system errors - try next URL
                        continue

            if module_file is None:
                return Result.error(f"Module '{current_module}' not found in local paths {self._local_paths} or URLs {self._url_bases}")

            # Load YAML
            try:
                with open(module_file, 'r') as f:
                    module_content = yaml.safe_load(f)
            except (OSError, yaml.YAMLError) as e:
                return Result.error(f"Failed to load YAML from '{module_file}': {e}")

            if module_content is None:
                module_content = {}

            # Process widgets - namespace by module name
            widgets = module_content.get("widgets", {})
            for widget_name, widget_def in widgets.items():
                full_name = f"{current_module}.{widget_name}"
                if full_name in self._widget_definitions:
                    return Result.error(f"Duplicate widget definition: '{full_name}'")
                self._widget_definitions[full_name] = widget_def

            # Process data - merge by key
            data = module_content.get("data", {})
            for data_name, data_def in data.items():
                if data_name in self._data_definitions:
                    return Result.error(f"Duplicate data definition: '{data_name}'")
                self._data_definitions[data_name] = data_def

            # Process app - only one allowed
            app = module_content.get("app")
            if app is not None:
                if self._app_config is not None:
                    return Result.error(f"Multiple 'app' sections found in module '{current_module}'")
                self._app_config = app

            # Add imports to queue
            imports = module_content.get("import", [])
            if imports:
                queue.extend(imports)

        # Validate final state
        if not self._widget_definitions:
            return Result.error("No widget definitions found after loading all modules")

        if self._app_config is None:
            return Result.error("No 'app' section found in any module")

        return Ok(None)

    @property
    def widget_definitions(self) -> Dict[str, dict]:
        """Get all loaded widget definitions"""
        return self._widget_definitions

    @property
    def data_definitions(self) -> Dict[str, dict]:
        """Get all loaded data definitions"""
        return self._data_definitions

    @property
    def app_config(self) -> Optional[dict]:
        """Get app configuration"""
        return self._app_config

    def dispose(self) -> Result[None]:
        """Cleanup resources"""
        self._widget_definitions.clear()
        self._data_definitions.clear()
        self._app_config = None
        return Ok(None)
