"""
Generic application runner for imery
"""

import sys
import click
from pathlib import Path
from imgui_bundle import imgui
from imery.lang import Lang
from imery.frontend.widget_factory import WidgetFactory
from imery.backend.kernel import Kernel
from imery.plugin_manager import PluginManager
from imery.backend.data_tree import DataTree
from imery.dispatcher import Dispatcher
from imery.types import DataPath
from imery.result import Result

import time

init_time = time.time()

# Global state
factory = None
dispatcher = None
kernel = None
data_tree = None


def handle_error(err):
    import yaml
    print(yaml.dump(err.as_tree))
    if sys.platform != 'emscripten':
        sys.exit(-1)


@click.command()
@click.option('--layouts-path', '-p',
              envvar='IMERY_LAYOUTS_PATH',
              type=str,
              multiple=True,
              help='Colon-separated list of directories to search for layout modules (can be specified multiple times)')
@click.option('--layouts-url', '-u',
              envvar='IMERY_LAYOUTS_URL',
              type=str,
              multiple=True,
              help='URL to download layouts from (can be specified multiple times, e.g., GitHub raw URLs)')
@click.option('--plugins-path',
              envvar='IMERY_PLUGINS_PATH',
              type=str,
              help='Colon-separated list of directories to search for provider modules')
@click.option('--widgets-path',
              envvar='IMERY_WIDGETS_PATH',
              type=str,
              help='Colon-separated list of directories to search for widget modules')
@click.option('--main', '-m',
              required=True,
              type=str,
              help='Name of the main module to load')

def main(layouts_path, layouts_url, plugins_path, widgets_path, main):
    """Imery application runner"""
    global main_widget, factory, dispatcher, kernel, data_tree

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
    lang_res = Lang.create(layouts_paths=layouts_paths)
    if not lang_res:
        click.echo(f"Error creating Lang: {lang_res}", err=True)
        return 1

    lang = lang_res.unwrapped

    load_res = lang.load_main_module(main)
    if not load_res:
        click.echo(f"Error loading main module '{main}': {load_res}", err=True)
        return 1

    # Create Dispatcher
    dispatcher_res = Dispatcher.create()
    if not dispatcher_res:
        click.echo(f"Error creating Dispatcher: {dispatcher_res}", err=True)
        return 1
    dispatcher = dispatcher_res.unwrapped

    # Create PluginManager
    plugin_manager_res = PluginManager.create(label="devices", plugins_path=plugins_path)
    if not plugin_manager_res:
        click.echo(f"Error creating PluginManager: {plugin_manager_res}", err=True)
        return 1
    plugin_manager = plugin_manager_res.unwrapped

    # Create Kernel
    kernel_res = Kernel.create(dispatcher=dispatcher, plugin_manager=plugin_manager)
    if not kernel_res:
        click.echo(f"Error creating Kernel: {kernel_res}", err=True)
        return 1
    kernel = kernel_res.unwrapped

    # Create WidgetFactory with kernel as a named tree
    data_trees = {"kernel": kernel}
    res = WidgetFactory.create(dispatcher, widget_definitions=lang.widget_definitions, data_trees=data_trees, widgets_path=widgets_path)
    if not res:
        handle_error(res)
        click.echo(f"Error creating WidgetFactory: {factory_res}", err=True)
        return 1
    factory = res.unwrapped

    # Get app config
    app_config = lang.app_config
    if not app_config:
        click.echo("Error: No app configuration found", err=True)
        return 1

    widget_name = app_config.get('widget')
    data_name = app_config.get('data')

    if not widget_name:
        click.echo("Error: app.widget not specified", err=True)
        return 1

    if not data_name:
        click.echo("Error: app.data not specified", err=True)
        return 1

    # Prepend main module namespace if widget_name doesn't have one
    # (composite widgets do this automatically, but app entry point needs it too)
    if '.' not in widget_name:
        widget_name = f"{main}.{widget_name}"

    # Get data definition
    data_definitions = lang.data_definitions
    if data_name not in data_definitions:
        click.echo(f"Error: data '{data_name}' not found", err=True)
        return 1

    data_def = data_definitions[data_name]

    # Substitute builtins in children
    if 'children' in data_def:
        children = data_def['children']
        for key, value in children.items():
            if isinstance(value, str) and value == '$kernel':
                children[key] = kernel

    # Create DataTree
    data_tree = DataTree(data_def)

    # Create main widget
    widget_res = factory.create_widget(widget_name, data_tree, DataPath("/"))
    if not widget_res:
        click.echo(f"Error creating widget '{widget_name}': {widget_res}", err=True)
        return 1

    main_widget = widget_res.unwrapped

    # Run application - the main widget handles everything
    return main_widget.run()


if __name__ == '__main__':
    if sys.platform == 'emscripten':
        # In Pyodide/Emscripten, don't let Click call sys.exit()
        main(standalone_mode=False)
    else:
        main()
