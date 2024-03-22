import argparse
import inspect
import os
import sys
from typing import Any, Dict, List, Tuple, Type

import qcmanager.procedures as procedures
from qcmanager.hw import TBController
from qcmanager.procedures._parsing import get_procedure_args
from qcmanager.session import Session


def main(*args):
    parser = create_argparser()
    args = parser.parse_args(args)
    session, run_procedure = initialize_required_interfaces(args)
    run_args = extract_run_args(run_procedure, args, session)
    session.handle_procedure(run_procedure, procedure_arguments=run_args)


def create_argparser():
    parser = argparse.ArgumentParser(
        "Running single procedures via command lines",
    )
    parser = add_tileboard_args(parser)
    parser = add_session_args(parser)

    cmd_parser = parser.add_subparsers(dest="procedure")
    for method_class in procedures.__all_procedures__:
        cmd_parser = create_procedure_subparser(cmd_parser, method_class)

    return parser


def add_tileboard_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """
    No options are set as manditory since the certain processes can require
    that the tileboard interface be not set up.
    """
    group = parser.add_argument_group("Tileboard controller connection options")
    group.add_argument("--hexaip", type=str, help="IP of the tileboard controller")
    group.add_argument(
        "--i2c_port", type=int, default=5555, help="Port for I2C control server"
    )
    group.add_argument(
        "--daq_port", type=int, default=6000, help="Port of DAQ control server"
    )
    group.add_argument(
        "--pull_port", type=int, default=6001, help="Port for DAQ pulling server"
    )
    group.add_argument("--base_config_file", type=str, help="Base configuration file")
    return parser


def add_session_args(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    group = parser.add_argument_group(
        "Tileboard session initialization, required for all standalone runs"
    )
    group.add_argument("--board_type", type=str, required=True, help="Board type")
    group.add_argument("--board_id", type=str, required=True, help="Board id")
    return parser


def create_procedure_subparser(
    cmd_parser: argparse.ArgumentParser, method_class
) -> argparse.ArgumentParser:
    sub_parser = cmd_parser.add_parser(
        method_class.__name__,
        description=method_class.__doc__,
        help=method_class.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    for name, param in get_procedure_args(method_class).items():
        hint = param.annotation
        argument_settings = {}
        argument_settings["type"] = hint.__origin__
        argument_settings["help"] = procedures._parsing.get_param_doc(param)
        # Adding default arugment
        if not procedures._parsing.has_default(param):
            argument_settings["required"] = True
        else:
            argument_settings["default"] = param.default

        sub_parser.add_argument("--" + name, **argument_settings)
    return cmd_parser


def initialize_required_interfaces(
    args: argparse.Namespace,
) -> Tuple[Session, Type, List[Any]]:
    # Loading the saved session
    if not args.procedure:
        raise ValueError("Procedure must be defined")

    session = Session()
    session_file = f"results/{args.board_type}.{args.board_id}/session.yaml"
    if os.path.exists(os.path.dirname(session_file)):
        session.load_yaml(session_file)
    else:
        session.from_blank("1234", "5678")

    method_class = getattr(procedures, args.procedure)
    for param in inspect.signature(method_class.run).parameters.values():
        arg_type = param.annotation
        if arg_type == TBController:
            session.tb_controller = TBController(
                ip=args.hexaip,
                daq_port=args.daq_port,
                pull_port=args.pull_port,
                i2c_port=args.i2c_port,
                pull_ip="local_host",
                config_file=args.base_config_file,
            )

    return session, method_class


def extract_run_args(
    run_procedure: Type, args: argparse.Namespace, session: Session
) -> Dict[str, Any]:
    for name, param in get_procedure_args(run_procedure).items():
        procedures._parsing.run_argument_parser(
            param, getattr(args, name), session, exception=True
        )
    return {
        name: getattr(args, name) for name in get_procedure_args(run_procedure).keys()
    }


if __name__ == "__main__":
    import logging

    logging.root.setLevel(logging.NOTSET)
    logging.basicConfig(level=logging.NOTSET)
    main(*sys.argv[1:])
