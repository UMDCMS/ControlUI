import os

import matplotlib
import numpy

from ..yaml_format import ProcedureResult
from .common import PlottingBase


class dummy_process2(PlottingBase):

    @PlottingBase.common_validity_check
    def fig_figure_1(self, result: ProcedureResult) -> matplotlib.figure.Figure:
        fig, ax = self.make_simple_figure()
        ax.set_xlabel("AWESOME X")
        ax.set_ylabel("AWESOME Y")
        return fig

    @PlottingBase.common_validity_check
    def fig_figure_2(self, result: ProcedureResult) -> matplotlib.figure.Figure:
        fig, ax = self.make_simple_figure()
        ax.set_xlabel("ANOTHER AWESOME X")
        ax.set_ylabel("ANOTHER AWESOME Y")
        return fig

    @PlottingBase.common_validity_check
    def fig_figure_3(self, result: ProcedureResult) -> matplotlib.figure.Figure:
        fig, ax = self.make_simple_figure()
        ax.set_xlabel("YET ANOTHER AWESOME X")
        ax.set_ylabel("YET ANOTHER AWESOME Y")
        return fig
