import awkward
import hist
import matplotlib
import numpy

from ..procedures._array_processing import get_hgcroc_array
from ..yaml_format import ProcedureResult
from .common import PlottingBase


class led_scan_testbeam(PlottingBase):
    @PlottingBase.common_validity_check
    def fig_adc_profile(self, result: ProcedureResult) -> matplotlib.figure.Figure:
        array = self.get_hgcroc_array(result)
        h_adc = hist.Hist(
            hist.axis.Integer(0, 1024, name="adc"),
            hist.axis.Integer(0, 100, name="channel"),
            hist.axis.Regular(0, 50, 32, name="time"),
        )
        h_adc.fill(adc=array.adc, channel=array.channel, time=array.time)
        h_adc = h_adc.profile("adc")  # We are only interested in the overall profile

        fig, ax = PlottingBase.make_simple_figure()

        for channel in range(0, 72):
            h_adc[channel].plot(ax=ax, label="channel")

        ax.set_xlabel("Time [ns]")
        ax.set_ylabel("ADC [bits]")

        return fig

    def fig_tot_profile(self, result: ProcedureResult) -> matplotlib.figure.Figure:
        array = self.get_hgcroc_array(result)
        h_adc = hist.Hist(
            hist.axis.Integer(0, 1024, name="tot"),
            hist.axis.Integer(0, 100, name="channel"),
            hist.axis.Regular(0, 50, 32, name="time"),
        )
        h_adc.fill(adc=array.adc, channel=array.channel, time=array.time)
        h_adc = h_adc.profile("tot")  # We are only interested in the overall profile

        fig, ax = PlottingBase.make_simple_figure()

        for channel in range(0, 72):
            h_adc[channel].plot(ax=ax, label="channel")

        ax.set_xlabel("Time [ns]")
        ax.set_ylabel("Time-over-thresholds [bits]")

        return fig

    def _make_array(self, result: ProcedureResult) -> awkward.Array:
        # Getting the list file
        return get_hgcroc_array(
            filter(lambda x: x.path.endswith(".raw"), result.data_files), self.base_path
        )
