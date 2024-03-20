import inspect
import warnings
from typing import Callable, Dict, Iterable, List, Type, _AnnotatedAlias

from ..hw import TBController
from ..utils import _str_
from ..yaml_format import ProcedureResult
from ._procedure_base import ProcedureBase


def get_procedure_args(method_class: Type) -> Dict[str, inspect.Parameter]:
    """Returning a list of parameters that requires user-level settings"""
    return {
        name: param
        for name, param in inspect.signature(method_class.__init__).parameters.items()
        if name != "self" and name != "*" and name != "store_base"
    }


def __check_valid_inheritance__(method_class: Type):
    assert issubclass(
        method_class, ProcedureBase
    ), f"Procedure [{method_class.__name__}] is not inherited from ProcedureBase!"


def __check_valid_arg__(method_class: Type) -> bool:
    """
    Checking that the procedures method defined to declare the methods have a
    valid are correctly annotated
    """
    args_sig = get_procedure_args(method_class)
    illegal_args = []
    for arg_name, arg_sig in args_sig.items():
        if not isinstance(arg_sig.annotation, _AnnotatedAlias):
            illegal_args.append(arg_name)
    if len(illegal_args):
        name = method_class.__name__
        args = ", ".join(illegal_args)
        raise TypeError(
            _str_(
                f"""
                Procedure [{name}] has arguments ({args}) that is not
                annotated! Check file [{inspect.getfile(method_class)}]
                """
            )
        )


def __check_valid_interface__(method_class: Type) -> bool:
    """
    Checking the hardware interfaces requested by the file.
    """
    __known_type__ = [
        List[ProcedureResult],
        TBController,
        Callable[[Iterable], Iterable],
    ]
    missing_type = []
    unknown_type = []

    for param_name, param in inspect.signature(method_class.run).parameters.items():
        if param_name == "self":
            continue
        if param.annotation == inspect._empty:
            missing_type.append(param_name)
        elif param.annotation not in __known_type__:
            unknown_type.append(param_name)

    if len(missing_type):
        name = method_class.__name__
        args = ", ".join(missing_type)
        raise TypeError(
            _str_(
                f"""
                Procedure [{name}.run] contains interfaces ({args}) without
                type specification. Check file
                [{inspect.getfile(method_class)}]
                """
            )
        )
    if len(unknown_type):
        name = method_class.__name__
        args = ", ".join(unknown_type)
        warnings.simplefilter("always", DeprecationWarning)
        warnings.warn(
            _str_(
                f"""
                Procedure [{name}] defined interfaces ({args}) with unknown
                type specification. Will attempt to match using parameter name,
                but the results are not guarateed to be correct. Contact the
                developers if you think this is an error.
                """
            ),
            DeprecationWarning,
        )


def get_param_type(param: inspect.Parameter) -> Type:
    return param.annotation.__origin__


def get_param_doc(param: inspect.Parameter) -> str:
    if len(param.annotation.__metadata__):
        return param.annotation.__metadata__[0]
    else:
        return ""


def has_default(param: inspect.Parameter) -> bool:
    """Checking if it has default value"""
    return param.default != inspect._empty
