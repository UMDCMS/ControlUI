import inspect
import warnings
from typing import Callable, Dict, Iterable, List, Optional, Type, _AnnotatedAlias

from ..hw import TBController
from ..utils import _str_
from ..yaml_format import ProcedureResult
from ._argument_validation import ArgumentValueChecker
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


"""
Methods for checking the procedure arguments are written according to
specifications.
"""


def __check_valid_arg__(method_class: Type) -> bool:
    """
    Top level function
    """
    __check_arg_empty_annotation__(method_class)
    args_sig = get_procedure_args(method_class)
    illegal_args = []
    for arg_name, arg_sig in args_sig.items():
        if not isinstance(arg_sig.annotation, _AnnotatedAlias):
            illegal_args.append(arg_name)
        # TODO: Check for allowed argument types?
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


def __raise_illegal_args__(method_class: Type, arg_list: List[str], desc: str) -> str:
    name = method_class.__name__
    args = ", ".join(arg_list)
    raise TypeError(
        _str_(
            f"""
            Procedure [{name}] has arguments ({args}) {desc}! Check file
            [{inspect.getfile(method_class)}]
            """
        )
    )


def __check_arg_empty_annotation__(method_class: Type):
    """
    If an argument is completely not annotated it will not be recognized by the
    dataclass decorator and cannot be access in the __init__ methods. These
    shall not be allowed.
    """
    args_sig = get_procedure_args(method_class)
    non_annotated_args = [
        x
        for x in method_class.__dict__.keys()
        if not x.startswith("_")
        and x not in args_sig.keys()
        and not callable(getattr(method_class, x))
    ]
    if len(non_annotated_args) > 0:
        __raise_illegal_args__(
            method_class, non_annotated_args, "that does not contain annotations"
        )


def __check_annotation_type__(procedure_class):
    # Types for fails to check for
    no_anno_args = []
    no_doc_args = []
    bad_type_args = []

    __allowed_types__ = [str, int, float]

    for arg_name, arg_sig in get_procedure_args(procedure_class).items():
        if not isinstance(arg_sig.annotation, _AnnotatedAlias):
            no_anno_args.append(arg_name)
        if len(arg_sig.annotation.__metadata__) < 0:
            no_doc_args.append(arg_name)
        if not isinstance(arg_sig.annotation.__metadata__, str):
            no_doc_args.append(arg_name)
        if arg_sig.annotation.__origin__ not in __allowed_types__:
            bad_type_args.append(arg_name)

        # TODO: Additional checks to run?

    if len(no_anno_args):
        __raise_illegal_args__(
            procedure_class, no_anno_args, "not annotated with [typing.Annotated]"
        )
    if len(no_doc_args):
        __raise_illegal_args__(
            procedure_class, no_doc_args, "do not contain documentation string"
        )
    if len(bad_type_args):
        __raise_illegal_args__(
            procedure_class, bad_type_args, "requesting non-primitive types"
        )


"""
Checking that the run method has understood interface types, which is used to
automatically call the various function methods in the handling methods.
"""


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


def get_parser(param: inspect.Parameter) -> Optional[ArgumentValueChecker]:
    if len(param.annotation.__metadata__) > 1:
        return param.annotation.__metadata__[1]
    else:
        return None


def run_argument_parser(
    param: inspect.Parameter, value, session, exception=False
) -> bool:
    parser = get_parser(param)
    if parser is None:  # Always return true if parse is not set by designer
        return True
    parser = param.annotation.__metadata__[1]
    parser.session = session
    ret = parser._check_valid(value)
    if not exception:
        return ret
    else:
        if ret:
            return ret
        else:
            raise ValueError(
                f"Input value [{value}] failed annotated requirement [{parser}]"
            )
