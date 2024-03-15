import argparse
import importlib

import qcmanager


def main():
    parser = argparse.ArgumentParser("Running the plot generator standalone")
    parser.add_argument("--session", type=str, required=True, help="Session yaml file")
    parser.add_argument(
        "--idx", type=int, nargs="+", help="Index of the results you want to plot"
    )
    parser.add_argument("--prefix", type=str, default="", help="Plot name prefix")
    args = parser.parse_args()

    # Loadng the session
    session = qcmanager.session.Session()
    session.load_yaml(args.session)

    for idx in session.iterate(args.idx, desc="Running plot for result"):
        try:
            plot_single_procedure(session.results[idx], session, prefix=args.prefix)
        except Exception as err:
            print("Failed to plot results for index ", idx)
            print(str(err))
            raise err


def plot_single_procedure(
    result: qcmanager.yaml_format.ProcedureResult,
    session: qcmanager.session.Session,
    prefix: str,
):
    try:
        module = importlib.import_module(f"qcmanager.plotting.{result.name}")
    except ImportError:
        raise RuntimeError(
            f"Plotting routine for procedure [{result.name}] not defined"
        )

    plot_class = getattr(module, module.__name__.split(".")[-1])
    plotter = plot_class(base_path=session.save_base)
    for name, func in plotter.figure_methods.items():
        fig = func(result)

        save_name_elements = [
            result.name,
            name.replace("fig_", ""),
            qcmanager.utils.timestampf(result.end_time),
        ]
        if prefix != "":
            save_name_elements.insert(0, prefix)
        fig.savefig("_".join(save_name_elements) + ".pdf")


if __name__ == "__main__":
    main()
