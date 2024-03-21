from dataclasses import dataclass
from typing import Annotated, Callable, Dict, List, Tuple

import hist
import nested_dict
import yaml

from ..hw import TBController
from ..yaml_format import ProcedureResult, SingularResult
from ._array_processing import get_hgcroc_array
from ._procedure_base import HWIterable, ProcedureBase


@dataclass(kw_only=True)
class led_scan_testbeam(ProcedureBase):
    """Getting the number of items"""

    # Related to scanning
    startBX: Annotated[int, "BX offset scanning start value"] = 0x10 + 25
    stopBX: Annotated[int, "BX off set scanning stop value"] = 0x10 + 25 + 2
    startTrim: Annotated[int, "Trim scan start value"] = 0
    stopTrim: Annotated[int, "Trim scan stop value"] = 3
    startPhase: Annotated[int, "Phase scan start value"] = 0
    stopPhase: Annotated[int, "Phase scan stop value"] = 15

    # Related to data acquisition settings
    n_events: Annotated[int, "Number of events to take per scan"] = 2500

    def __post_init__(self):
        super().__post_init__()
        # Add none-user adjust able items here. This will be passed to the non data
        self.inject_config = {  # Notice that this will be used for many
            "gain": 1,  # 0 in original
            "calib": 0,  # 900 in original
            "injectedChannels": [13, 26, 28, 36, 45],
            "LEDvolt": 6800,  # LED_BIAS (LED amplitude) in mV  #------------added for sampling scan ext
            "OV": 4,  # SiPM overvoltage   #------------added for sampling scan extn # if OV > 10, OV = OV/10
        }

    def run(self, tbc: TBController, iterate: HWIterable) -> ProcedureResult:
        # Iterating over the various settings
        for trim, BX, phase in iterate(
            [
                (t, b, p)
                for t in range(self.startTrim, self.stopTrim)
                for b in range(self.startBX, self.stopBX)
                for p in range(self.startPhase, self.stopPhase)
            ],
            desc="Varying the tileboard configurations",
        ):
            tbc.daq_socket._config["daq"]["menus"]["calibAndL1A"].update(
                {
                    "calibType": "CALPULEXT",
                    "lengthCalib": 4,
                    "bxCalib": 0x10,
                    "prescale": 25,
                    "lengthL1A": 1,
                    "bxL1A": BX,
                }
            )
            tbc.daq_socket.configure()
            tbc.i2c_socket.configure(
                self.make_i2c_configuration(tbc, trim=trim, phase=phase)
            )
            tbc.i2c_socket.set_gbtsca_gpio_vals(0x00000080, 0x00000080)
            tbc.i2c_socket.resettdc()  # Reset MasterTDCs

            # Running the master configuration
            self.acquire_hgcroc(
                tbc,
                n_events=self.n_events,
                path=f"{self.name}_trim{trim}_BX{BX}_Phase{phase}.raw",
                desc="LED inject scan files",
                # Additional information to inject into the metadata
                BX=BX,
                phase=phase,
                trim=trim,
            )

        # Getting the analysis
        self.loginfo("Running the analysis of the final output")
        full_array = get_hgcroc_array(self.result.data_list)
        full_array["time"] = (full_array.BX * 16 + full_array.phase) * (25.0 / 16.0)
        h_adc = hist.Hist(
            hist.axis.Integer(0, 1024, name="adc"),
            hist.axis.Integer(0, 100, name="channel"),
            hist.axis.Regular(0, 50, 32, name="time"),
        )
        h_adc.fill(adc=full_array.adc, channel=full_array.channel, time=full_array.time)
        h_adc = h_adc.profile("adc")  # We are only interested in the overall profile
        h_tot = hist.Hist(
            hist.axis.Integer(0, 1024, name="tot"),
            hist.axis.Integer(0, 100, name="channel"),
            hist.axis.Regular(0, 50, 32, name="time"),
        )
        h_tot.fill(tot=full_array.tot, channel=full_array.channel, time=full_array.time)
        h_tot = h_tot.profile("tot")
        h_toa = hist.Hist(
            hist.axis.Integer(0, 1024, name="toa"),
            hist.axis.Integer(0, 100, name="channel"),
            hist.axis.Regular(0, 50, 32, name="time"),
        )
        h_toa.fill(toa=full_array.toa, channel=full_array.channel, time=full_array.time)
        h_toa = h_toa.profile("toa")

        bad_channels = []
        for channel in self.inject_config["injectedChannels"]:
            # TODO Additional parsing according to injection results
            self.result.channel_summary.append(
                SingularResult(channel=channel, status=0, desc="Success", best_phase=10)
            )
            # bad_channels.append()

        self.result.board_summary = SingularResult(
            channel=SingularResult.BOARD,
            status=1 if len(bad_channels) != 0 else 0,
            desc="contail bad channels" if len(bad_channels) != 0 else "Success",
            bad_channel=bad_channels,
        )

        self.loginfo("Updating the settings to the final results")
        self.save_full_config(
            tbc, path="led_scan_config.yaml", desc="led scan corrected configuration"
        )

        return self.result

    def _make_i2c_configuration(self, tbc: TBController, trim_value: int, phase: int):
        # Aliases for underlying inject configurations
        _GAIN = self.inject_config["gain"]
        _CHANNELS = self.inject_config["injectedChannels"]

        config = nested_dict()
        for key in tbc.i2c_socket._config.keys():
            if key.find("roc_s") != 0:
                continue
            config[key]["sc"]["ReferenceVoltage"]["all"]["IntCtest"] = 0
            config[key]["sc"]["ReferenceVoltage"]["all"]["Calib"] = 0
            # "1": inject to preamp input, "0": inject to conveyor input
            config[key]["sc"]["ReferenceVoltage"]["all"]["choice_cinj"] = 1
            config[key]["sc"]["ReferenceVoltage"]["all"]["cmd_120p"] = 0
            # ================================test21072023
            config[key]["sc"]["ch"]["all"]["trim_inv"] = trim_value

            if _GAIN == 2 or _GAIN == 1 or _GAIN == 0:
                for inj_chs in _CHANNELS:
                    config[key]["sc"]["ch"][inj_chs]["LowRange"] = 0
                    config[key]["sc"]["ch"][inj_chs]["HighRange"] = 0

            config[key]["sc"]["Top"]["all"]["phase_strobe"] = 15 - phase
        return config.to_dict
