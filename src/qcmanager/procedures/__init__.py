# For parsing purposes
import importlib

from . import _parsing, _procedure_base

# Define the procedures that you want to include into the main processes. This
# expects that the procedure classes are defined as in the file <name>.py with
# identical class name. Notice that the order of this list will determine the
# ordering by which it will appear in the GUI
__all_procedures_names__ = [
    "dummy_process2",
    "dummy_procedure",
    # "pedestal_correction",
]

# Peforming additional parsing
__current__ = importlib.import_module(__package__)
__all_procedures__ = []
for procedure_name in __all_procedures_names__:
    procedure_class = importlib.import_module(f".{procedure_name}", __package__)
    procedure_class = getattr(procedure_class, procedure_name)
    if not isinstance(procedure_class, type):
        continue

    # Additional parsing to do
    _parsing.__check_valid_inheritance__(procedure_class)
    _parsing.__check_valid_arg__(procedure_class)
    _parsing.__check_valid_interface__(procedure_class)
    __all_procedures__.append(procedure_class)
    setattr(__current__, procedure_name, procedure_class)
