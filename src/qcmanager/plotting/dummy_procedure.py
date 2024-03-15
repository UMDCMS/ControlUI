import os

import matplotlib
import numpy

from ..yaml_format import ProcedureResult
from .common import PlottingBase


class dummy_procedure(PlottingBase):
    @PlottingBase.common_validity_check
    def fig_mean_compare(self, result: ProcedureResult) -> matplotlib.figure.Figure:
        fig, ax = self.make_simple_figure()
        ax.set_xlabel("Channel index")
        ax.set_ylabel("Mean value [ADC]")
        plot_entry_list = []

        initial_file = self.get_data_path(
            next(x for x in result.data_files if x.desc == "Initial readout"),
        )
        initial_arr = numpy.load(initial_file)

        plot_entry_list.append(
            ax.errorbar(
                x=numpy.arange(initial_arr.shape[0]),
                y=numpy.mean(initial_arr, axis=-1),
                yerr=numpy.std(initial_arr, axis=-1),
                color="black",
                marker="o",
                ls="none",
                label="Initial",
            )
        )

        final_file = self.get_data_path(
            next(x for x in result.data_files if x.desc == "Final_readout"),
        )
        final_arr = numpy.load(final_file)
        plot_entry_list.append(
            ax.errorbar(
                x=numpy.arange(final_arr.shape[0]) + 0.1,
                y=numpy.mean(final_arr, axis=-1),
                yerr=numpy.std(final_arr, axis=-1),
                color="red",
                marker="s",
                ls="none",
                label="Final",
            )
        )
        self.create_interactive_legend(fig, ax, plot_entry_list, loc="upper right")

        return fig

    @PlottingBase.common_validity_check
    def fig_fit_compare(self, result: ProcedureResult) -> matplotlib.figure.Figure:
        fig, ax = self.make_simple_figure()
        fig.set_figwidth(fig.get_figheight() * 1.65)
        ax.set_xlabel("Shift value")
        ax.set_ylabel("Mean value [ADC]")

        plot_arr = []

        for shift_desc in result.data_files:
            if "shifted" not in shift_desc.desc:
                continue
            file_path = self.get_data_path(shift_desc)
            arr = numpy.load(file_path)
            mean = numpy.mean(arr, axis=-1)
            err = numpy.std(arr, axis=-1)
            shift = numpy.ones_like(mean) * shift_desc.shift
            plot_arr.append([shift, mean, err])

        plot_arr = numpy.array(plot_arr)  # Converting for nicer slicing
        plot_entry_list = []

        for channel in range(plot_arr.shape[-1]):
            plot_entry_list.append(
                ax.errorbar(
                    x=plot_arr[:, 0, channel],
                    y=plot_arr[:, 1, channel],
                    yerr=plot_arr[:, 2, channel],
                    marker="o",
                    ls="none",
                    label=f"ch.{channel}",
                )
            )

        self.create_interactive_legend(
            fig,
            ax,
            plot_entry_list,
            loc="center left",
            title="channels",
            bbox_to_anchor=(1.001, 0.50),
            ncols=4,
        )
        return fig
