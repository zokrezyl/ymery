
_pending_widgets = []
def widget(obj):
    _pending_widgets.append(obj)
    return obj


_pending_device_managers = []
def device_manager(obj):
    _pending_device_managers.append(obj)
    return obj

_pending_devices = []
def device(obj):
    _pending_devices.append(obj)
    return obj
