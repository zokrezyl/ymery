"""
Generic application runner for ymery
"""

import sys
import logging
import click
from pathlib import Path
from imgui_bundle import imgui, immapp
from ymery.lang import Lang
from ymery.frontend.widget_factory import WidgetFactory
from ymery.plugin_manager import PluginManager
from ymery.dispatcher import Dispatcher
from ymery.types import DataPath
from ymery.result import Result, Ok
from ymery.frontend.widget import render_error
from ymery.logging import setup_logging, get_ring_buffer
from ymery.data_bag import DataBag

import time

init_time = time.time()


def show_if_error(err) -> Result[None]:
    """Run a simple imgui loop to display an error"""
    if err:
        return err
    error_tree = err.as_tree if hasattr(err, 'as_tree') else {"error": str(err)}
    logging.error(error_tree)

    def gui_loop():
        imgui.text("The app could not be initialized due to the errors below. Click 'exit' to terminate the app")
        if imgui.button("exit"):
            sys.exit(-1)
        render_error(error_tree)

    immapp.run(
        gui_function=gui_loop,
        window_title="Ymery - Error",
        window_size=(800, 600)
    )
    return Ok(None)


@click.command()
@click.option('--layouts-path', '-p',
              envvar='YMERY_LAYOUTS_PATH',
              type=str,
              multiple=True,
              help='Colon-separated list of directories to search for layout modules (can be specified multiple times)')
@click.option('--layouts-url', '-u',
              envvar='YMERY_LAYOUTS_URL',
              type=str,
              multiple=True,
              help='URL to download layouts from (can be specified multiple times, e.g., GitHub raw URLs)')
@click.option('--plugins-path',
              envvar='YMERY_PLUGINS_PATH',
              type=str,
              help='Colon-separated list of directories to search for provider modules')
@click.option('--widgets-path',
              envvar='YMERY_WIDGETS_PATH',
              type=str,
              help='Colon-separated list of directories to search for widget modules')
@click.option('--main', '-m',
              required=True,
              type=str,
              help='Name of the main module to load')
@click.option('--log-level', '-l',
              envvar='YMERY_LOG_LEVEL',
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', '10', '20', '30', '40', '50']),
              default='INFO',
              help='Log level (DEBUG=10, INFO=20, WARNING=30, ERROR=40, CRITICAL=50)')
@click.option('--log-file', '-f',
              envvar='YMERY_LOG_FILE',
              type=str,
              default=None,
              help='Log file path (default: stdout)')

def main(layouts_path, layouts_url, plugins_path, widgets_path, main, log_level, log_file):
    """Ymery application runner"""
    global dispatcher, kernel, data_tree

    # Setup logging first
    level = getattr(logging, log_level) if log_level.isalpha() else int(log_level)
    setup_logging(level=level, log_file=log_file)

    # Combine layouts_path and layouts_url in order of specification
    # Both can be specified multiple times, precedence is order of appearance
    layouts_paths = []

    # Process --layouts-path (can be multiple, each colon-separated)
    if layouts_path:
        for path_spec in layouts_path:
            layouts_paths.extend(path_spec.split(':'))

    # Process --layouts-url (can be multiple)
    if layouts_url:
        layouts_paths.extend(layouts_url)

    # Default to current directory if nothing specified
    if not layouts_paths:
        layouts_paths = ['.']

    # Create Lang and load modules
    lang = show_if_error(Lang.create(layouts_paths=layouts_paths, main=main)).unwrapped

    # Create Dispatcher
    dispatcher = show_if_error(Dispatcher.create()).unwrapped

    # Build default plugin paths
    ymery_dir = Path(__file__).parent
    default_plugins_path = str(ymery_dir / "plugins" / "frontend") + ":" + str(ymery_dir / "plugins" / "backend")
    if plugins_path:
        plugins_path = default_plugins_path + ":" + plugins_path
    else:
        plugins_path = default_plugins_path

    # Create PluginManager
    plugin_manager = show_if_error(PluginManager.create(plugins_path=plugins_path)).unwrapped

    # Instantiate all data trees from lang.data_definitions
    data_trees = {}
    data_definitions = lang.data_definitions

    for data_name, data_def in data_definitions.items():
        # Get the type (tree-like class name)
        type_name = data_def.get('type')
        if not type_name:
            show_if_error(Result.error(f"Data '{data_name}' missing 'type' field"))
            return 1

        # Get the class from plugin_manager
        res = plugin_manager.get_metadata(DataPath(f"/tree-like/{type_name}"))
        if not res:
            show_if_error(Result.error(f"TreeLike type '{type_name}' not found for data '{data_name}'", res))
            return 1

        tree_like_class = res.unwrapped.get("class")
        if not tree_like_class:
            show_if_error(Result.error(f"No class found for TreeLike type '{type_name}'"))
            return 1

        # Get raw_arg if present
        raw_arg = data_def.get('arg')

        # Instantiate with standard args
        try:
            instance = tree_like_class(dispatcher, plugin_manager, raw_arg)
        except Exception as e:
            show_if_error(Result.error(f"Failed to instantiate '{type_name}' for data '{data_name}'", e))
            return 1

        # Initialize the instance
        res = instance.init()
        if not res:
            show_if_error(Result.error(f"Failed to init '{type_name}' for data '{data_name}'", res))
            return 1

        data_trees[data_name] = instance

    # Create WidgetFactory with all data trees
    widget_factory = show_if_error(WidgetFactory.create(dispatcher, plugin_manager, widget_definitions=lang.widget_definitions, data_trees=data_trees)).unwrapped

    # Get app config
    app_config = lang.app_config
    if not app_config:
        show_if_error(Result.error("No app configuration found"))
        return 1

    widget_name = app_config.get('widget')
    data_name = app_config.get('main-data')

    if not widget_name:
        show_if_error(Result.error("app.widget not specified"))
        return 1

    # If main-data not specified, use the first data tree if any exist
    if not data_name and data_trees:
        data_name = next(iter(data_trees.keys()))
        logging.info(f"No main-data specified, using first data tree: '{data_name}'")

    # Prepend main module namespace if widget_name doesn't have one
    if '.' not in widget_name:
        widget_name = f"{main}.{widget_name}"

    # Verify main data exists (if specified)
    if data_name and data_name not in data_trees:
        show_if_error(Result.error(f"Data '{data_name}' not found in data definitions"))
        return 1

    # Create root DataBag only if we have data trees
    root_data_bag = None
    if data_trees:
        res = DataBag.create(
            dispatcher=dispatcher,
            plugin_manager=plugin_manager,
            data_trees=data_trees,
            main_data_key=data_name,
            main_data_path=DataPath("/"),
            static=None
        )
        if not res:
            show_if_error(Result.error("Failed to create root DataBag", res))
            return 1
        root_data_bag = res.unwrapped

    # Create main widget - factory handles None data bag
    main_widget = show_if_error(widget_factory.create_widget(root_data_bag, widget_name)).unwrapped

    # Run application - the main widget handles everything
    return main_widget.run()


if __name__ == '__main__':
    if sys.platform == 'emscripten':
        # In Pyodide/Emscripten, don't let Click call sys.exit()
        main(standalone_mode=False)
    else:
        main()
