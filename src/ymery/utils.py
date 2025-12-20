from ymery.types import DataPath, Object
from typing import Dict

from ymery.result import Result, Ok

def call_by_path(obj, path: DataPath, what, params: Dict = None) -> Result[Object]:

    if what == "children-names":
        method_name = "get_children_names"
        attribute_name = "children"
    elif what == "metadata":
        method_name = "get_metadata"
        attribute_name = "metadata"
    elif what == "open":
        method_name = "open"
        attribute_name = "open"
    elif what == "configure":
        method_name = "configure"
        attribute_name = "configure"
    elif what == "close":
        method_name = "close"
        attribute_name = "close"
    elif what in ["register_opened_asset", "unregister_opened_asset"]:
        method_name = what
        attribute_name = what
    else:
        return Result.error(f"cannot handle {what}")

    # Check if obj is a dict (tree node) - if not, must have seed
    if not isinstance(obj, dict):
        return Result.error("call_by_path: object is not a dictionary and has no seed")

    seed_instance = obj.get("seed-instance")
    if seed_instance:
        # we do not cache, providers cache
        method = getattr(seed_instance, method_name)
        if what in ["open", "configure", "close"] and params is not None:
            return method(path, params)
        elif what in ["register_opened_asset", "unregister_opened_asset"] and params is not None:
            # register_opened_asset(relative_path, asset, metadata)
            # path here is /opened/providers, but we need to pass the relative path from params
            return method(params.get("path"), params.get("asset"), params.get("metadata"))
        else:
            return method(path)

    seed_class = obj.get("seed-class")
    if seed_class:
        constructor_args = obj.get("seed-constructor-args")
        if constructor_args:
            # Convert hyphenated keys to underscores for Python kwargs
            python_args = {k.replace('-', '_'): v for k, v in constructor_args.items()}
            res = seed_class.create(**python_args)
        else:
            res = seed_class.create()
        if not res:
            return Result.error("call_by_path: could not create seed instance", res)
        seed_instance = res.unwrapped
        obj["seed-instance"] = seed_instance
        method = getattr(seed_instance, method_name)
        if what in ["open", "configure", "close"] and params is not None:
            return method(path, params)
        elif what in ["register_opened_asset", "unregister_opened_asset"] and params is not None:
            # register_opened_asset(relative_path, asset, metadata)
            # path here is /opened/providers, but we need to pass the relative path from params
            return method(params.get("path"), params.get("asset"), params.get("metadata"))
        else:
            return method(path)

    # log(f"call_by_path: len path {len(path)}")
    if len(path) == 0:
        res = obj.get(attribute_name)
        if res is None:
            return Result.error(f"call_by_path: attribute '{attribute_name}' not found in path '{path}'")

        if what == "children-names":
            return Ok(list(res.keys()))
        else:
            return Ok(res)

    children = obj.get("children")
    if not children:
        return Result.error(f"call_by_path: attribute {attribute_name} not found in path '{path}'")

    child = children.get(path[0])
    if not child:
        return Result.error(f"call_by_path: child '{path[0]}' not found")

    return call_by_path(child, path[1:], what, params)
