import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Tuple

import matplotlib
import matplotlib.pyplot as plt

from ..yaml_format import DataEntry, ProcedureResult


@dataclass
class PlottingBase:
    base_path: str

    def get_data_path(self, data: DataEntry) -> str:
        return os.path.join(self.base_path, data.path)

    @property
    def figure_methods(self) -> Dict[str, Callable]:
        return {
            x.replace("fig_", ""): getattr(self, x)
            for x in self.__dir__()
            if x.startswith("fig_")
        }

    @classmethod
    def make_simple_figure(
        cls,
    ) -> Tuple[matplotlib.figure.Figure, matplotlib.axes.Axes]:
        fig = plt.figure(constrained_layout=True, figsize=plt.figaspect(1))
        ax = fig.add_subplot(111)
        ax.set_xlabel("", horizontalalignment="right", x=1.0)
        ax.set_ylabel("", horizontalalignment="right", y=1.0)
        return fig, ax

    @classmethod
    def common_validity_check(cls, f):
        def _wrap(inst, result: ProcedureResult):
            classname = f.__module__.split(".")[-1]
            assert (
                classname == result.name
            ), f"Mismatch names [F:{classname}/{result.name}]"
            assert result.status_code[0] == 0, "Procedure did not logically complete"
            return f(inst, result)

        return _wrap

    @classmethod
    def create_interactive_legend(
        cls,
        fig: matplotlib.figure.Figure,
        ax: matplotlib.axes.Axes,
        plot_entrys: List[Any],
        *args,
        **kwargs,
    ):
        kwargs.setdefault("fontsize", "small")
        kwargs.setdefault("title_fontsize", "small")
        legend = ax.legend(*args, **kwargs)

        legend_plot_map = {}

        for legend_entry, ax_entry in zip(legend.get_texts(), plot_entrys):
            legend_entry.set_picker(30)  # Enable picking on the legend line.
            legend_plot_map[legend_entry] = ax_entry

        legend._legend_title_box.set_picker(30)

        TARGET_ALPHA = 0.01 if len(plot_entrys) > 30 else 0.2

        def on_pick_all():
            vis = get_entry_visibility(next(x for x in legend_plot_map.values()))
            for leg_entry, ax_entry in legend_plot_map.items():
                set_entry_alpha(leg_entry, 0.2 if vis else 1.0)
                set_entry_alpha(ax_entry, TARGET_ALPHA if vis else 1.0)

        def on_pick_single(legend_entry):
            ax_entry = legend_plot_map[legend_entry]
            vis = toggle_entry_visibility(ax_entry, TARGET_ALPHA)
            legend_entry.set_alpha(0.2 if vis else 1.0)

        def on_pick(event):
            legend_entry = event.artist
            # Hide everything
            if legend_entry is legend._legend_title_box:
                on_pick_all()

            # Do nothing if the source of the event is not a legend line.
            if legend_entry in legend_plot_map:
                on_pick_single(legend_entry)

            fig.canvas.draw()

        fig.canvas.mpl_connect("pick_event", on_pick)
        return legend


def set_entry_alpha(entry: Any, alpha: float):
    if hasattr(entry, "set_alpha"):
        entry.set_alpha(alpha)
        return
    if isinstance(entry, list):
        entry[0].set_alpha(alpha)
        return
    if isinstance(entry, matplotlib.container.ErrorbarContainer):
        points, caps, bars = entry
        for c in caps:
            c.set_alpha(alpha)
        for b in bars:
            b.set_alpha(alpha)
        points.set_alpha(alpha)
        return


def get_entry_visibility(entry: Any) -> bool:
    def _get_vis(x):
        if x.get_alpha() is None:
            return True
        else:
            return x.get_alpha() == 1.0

    if isinstance(entry, list):
        return _get_vis(entry[0])

    if isinstance(entry, matplotlib.container.ErrorbarContainer):
        points, caps, bars = entry
        return _get_vis(bars[0])
    return True


def toggle_entry_visibility(entry: Any, off_alpha: float) -> bool:
    vis = get_entry_visibility(entry)
    set_entry_alpha(entry, off_alpha if vis else 1.0)
    return vis
