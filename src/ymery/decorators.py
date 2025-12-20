from ymery.stringcase import spinalcase

_pending_widgets = {}
def widget(name_or_cls=None):
    def decorator(cls):
        key = name_or_cls if isinstance(name_or_cls, str) else spinalcase(cls.__name__)
        _pending_widgets[key] = cls
        return cls
    if name_or_cls is None or isinstance(name_or_cls, str):
        return decorator
    _pending_widgets[spinalcase(name_or_cls.__name__)] = name_or_cls
    return name_or_cls


_pending_device_managers = {}
def device_manager(name_or_cls=None):
    def decorator(cls):
        key = name_or_cls if isinstance(name_or_cls, str) else spinalcase(cls.__name__)
        _pending_device_managers[key] = cls
        return cls
    if name_or_cls is None or isinstance(name_or_cls, str):
        return decorator
    _pending_device_managers[spinalcase(name_or_cls.__name__)] = name_or_cls
    return name_or_cls

_pending_devices = {}
def device(name_or_cls=None):
    def decorator(cls):
        key = name_or_cls if isinstance(name_or_cls, str) else spinalcase(cls.__name__)
        _pending_devices[key] = cls
        return cls
    if name_or_cls is None or isinstance(name_or_cls, str):
        return decorator
    _pending_devices[spinalcase(name_or_cls.__name__)] = name_or_cls
    return name_or_cls

_pending_tree_likes = {}
def tree_like(name_or_cls=None):
    def decorator(cls):
        key = name_or_cls if isinstance(name_or_cls, str) else spinalcase(cls.__name__)
        _pending_tree_likes[key] = cls
        return cls
    if name_or_cls is None or isinstance(name_or_cls, str):
        return decorator
    _pending_tree_likes[spinalcase(name_or_cls.__name__)] = name_or_cls
    return name_or_cls
