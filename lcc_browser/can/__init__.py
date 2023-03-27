import inspect
import os.path
import pathlib
import importlib
import pkgutil
from lcc_browser.can.connection import Connection

# load CAN driver plugins into a registry
can_drivers = {}
can_directory = pathlib.Path(__file__).parent.resolve()
for driver in pkgutil.iter_modules([os.path.join(can_directory, "drivers")]):
    driver_module = importlib.import_module(".drivers."+driver.name, package=__package__)
    can_interfaces = [obj for name, obj in inspect.getmembers(driver_module, inspect.isclass) if Connection in obj.__bases__]
    for can_interface in can_interfaces:
        can_drivers[can_interface.name] = can_interface
        print("Loading driver:", can_interface.name, can_interface)
