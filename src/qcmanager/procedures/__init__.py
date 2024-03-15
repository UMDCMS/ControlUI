# For parsing purposes
import importlib

from . import _parsing, _procedure_base

# For all other classes, we help reduce the verticle stack by custom imports
from .dummy_procedure import dummy_procedure
from .dummy_process2 import dummy_process2

# from .pedestal_correction import pedestal_correction

# Peforming additional parsing
__current__ = importlib.import_module(__package__)
__all_procedures__ = []
for process in __current__.__dir__():
    if process == "importlib":
        continue
    if process.startswith("_"):
        continue

    process = getattr(__current__, process)
    if not isinstance(process, type):
        continue

    # Additional parsing to do
    __all_procedures__.append(process)
    _parsing.__check_valid_inheritance__(process)
    _parsing.__check_valid_arg__(process)
    _parsing.__check_valid_interface__(process)
