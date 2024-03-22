import inspect
import os
from typing import Any, Dict, Iterable, List, Optional, Type

import tqdm
import yaml

from .hw import TBController
from .procedures._procedure_base import HWIterable, ProcedureBase
from .utils import _str_, timestampf, to_yaml
from .yaml_format import ProcedureResult


class Session(object):
    """
    Main class for handling all logging instances and the various hardware
    interfaces. Because this is the main handler for running the various
    routines, this should see all stateful instances required by the session.

    This class is also used to help with file path management, were all output
    files will be stored to the <LOCAL_STORE>/<BOARD_TYPE>.<BOARD_ID>/
    directory, including the generated yaml files. All procedure functions
    should simply store the files without any additional directory, and the
    helper functions here will move all relavent files to the desired path.
    """

    LOCAL_STORE = "results/"

    def __init__(self):
        # Entries to be stored to session YAML file
        self.board_type: str = ""
        self.board_id: str = ""
        self.results: List[ProcedureResult] = []

        # Used to point to board file
        self.log_file: Optional[str] = None

        # Persistence reference to hardware control interfaces
        self.tb_controller: Optional[TBController] = None

    @property
    def save_base(self):
        return os.path.join(Session.LOCAL_STORE, f"{self.board_type}.{self.board_id}")

    def modify_save_path(self, path):
        return_path = os.path.join(self.save_base, path)
        if not os.path.exists(os.path.dirname(return_path)):
            os.mkdir(os.path.dirname(return_path))
        return return_path

    def load_yaml(self, filepath: str):
        self.log_file = filepath
        with open(filepath, "r") as f:
            store_session = yaml.safe_load(f)
            self.board_type = store_session["board_type"]
            self.board_id = store_session["board_id"]
            self.results = [
                ProcedureResult.from_dict(x) for x in store_session["results"]
            ]
            self.log_file = filepath

    def from_blank(self, board_type: str, board_id: str):
        # Checking if directory exists. Create a new directory is it doesn't
        target_path = os.path.join(Session.LOCAL_STORE, f"{board_type}.{board_id}")
        if not os.path.exists(target_path):
            os.mkdir(target_path)
        else:
            raise RuntimeError(
                _str_(
                    f"""
                    Directory [{target_path}] already exists! Cannot safely
                    create a new session profile directory
                    """
                )
            )

        self.board_type = board_type
        self.board_id = board_id
        self.results = []
        self.log_file = os.path.join(self.save_base, "session.yaml")
        self.save_session()

    def save_session(self):
        """Flushing results to target file"""
        with open(self.log_file, "w") as f:
            to_yaml(
                {
                    k: v
                    for k, v in self.__dict__.items()
                    if k in ["board_type", "board_id", "results"]
                },
                f,
            )

    def detect_procedure_interface(self, method_class: ProcedureBase) -> List[Any]:
        """
        Returning a tuple of inputs that should be passed to the procedure.run
        method based on the annotations provided in the function signature.
        """

        def _get_interface(int_name: str, int_type: Type) -> Any:
            __type_map__ = {
                HWIterable: self.iterate,
                TBController: self.tb_controller,
                List[ProcedureResult]: self.results,
            }
            if int_type in __type_map__:
                return __type_map__.get(int_type)
            else:
                return getattr(self, int_name)

        return [
            _get_interface(param_name, param.annotation)
            for param_name, param in inspect.signature(
                method_class.run
            ).parameters.items()
            if param_name != "self"
        ]

    def handle_procedure(
        self,
        procedure_class: Type,
        procedure_arguments: Dict[str, Any],
    ) -> None:
        """
        Running the procedure defined by the class with the given user inputs.
        Hardware interfaces are detected automatically.
        - The procedure_arguments should match the arguments used to define
          procedure constructor.
        - One additional item that we will add here is to set the store_path of
          the procedure base on the procedure name and the current timestamp.
        """
        store_base = self.modify_save_path(
            procedure_class.__name__ + "_" + timestampf()
        )
        os.mkdir(store_base)
        procedure_instance = procedure_class(
            **procedure_arguments, store_base=store_base
        )
        self.results.append(procedure_instance.result)
        # Running additional parsing before processing
        try:
            for name, param in get_procedure_args(procedure_class).items():
                run_argument_parser(
                    param,
                    getattr(procedure_instance, name),
                    session=self,
                    exception=True,
                )
            result = procedure_instance.run_with(
                *self.detect_procedure_interface(procedure_class)
            )
            # For all the the results. The file path should be reset to be relative
            # to the session.yaml file
            for f in result.data_files:
                f.path = os.path.relpath(f.path, os.path.dirname(self.log_file))
        except Exception as err:
            self.result.status_code = (1, str(err))
        finally:
            self.save_session()

    def iterate(self, x: Iterable, *args, **kwargs):
        # Method to keep track of long loops. Will be over written in the GUI
        # session
        return tqdm.tqdm(x, *args, **kwargs)
