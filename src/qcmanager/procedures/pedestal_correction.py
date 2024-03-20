from dataclasses import dataclass
from typing import Annotated, Callable, Dict, List, Tuple

import numpy
import scipy
import yaml

from ..hw import TBController, rocv2
from ..utils import create_nested, merge_nested
from ..yaml_format import ProcedureResult, SingularResult
from ._procedure_base import ProcedureBase


@dataclass(kw_only=True)
class pedestal_correction(ProcedureBase):
    """
    Dummy procedure for testing. Notice that doc strings will be used to
    generate helper documentation!
    """

    base_config_file: Annotated[str, "Base configuration file"]
    target_pedestal: Annotated[int, "Target pedestal after normalization"]
    n_events: Annotated[int, "Number of events to collect"] = 5000
    lower_range: Annotated[int, "Lower shift range"] = -5
    upper_range: Annotated[int, "Upper shift range"] = 5
    bx_spacing: Annotated[int, "Bunch crossing spacing"] = 45

    def run(
        self,
        tb_controller: TBController,
        iterate: Callable,
        session_log: List[ProcedureResult],
        **kwargs,
    ) -> ProcedureResult:
        # Resetting the base configuration
        with open(self.base_config_file, "r") as f:
            base_config = yaml.safe_load(f)
        tb_controller.i2c_socket._config = base_config
        tb_controller.daq_socket._config = base_config
        tb_controller.pull_socket._config = base_config
        tb_controller.daq_socket.enable_fast_commands(random=1)
        tb_controller.daq_socket.l1a_settings(bx_spacing=self.bx_spacing)
        # Special input to that is dynamically created

        # Saving the initial readout for comparison
        self.acquire_hgcroc(
            tbc=tb_controller,
            n_events=self.n_events,
            save_path="pedestal_inital",
            desc="Initial pedestal",
        )

        # Making container for scan results, splitting the main loop to a different
        # method
        original_dacb_settings = {
            channel: tb_controller.i2c_socket._config["roc_s0"]["sc"]["ch"][channel][
                "Dacb"
            ]
            for channel in tb_controller.i2c_socket._config["roc_s0"]["sc"]["ch"].keys()
        }
        scan_results = self._run_scan(tb_controller, iterate, original_dacb_settings)

        # Parsing the results to calculate the best Dacb settings given scan result
        # and target pedestal value.
        fit_results = self._run_fit(original_dacb_settings, scan_results)
        self.result.channel_summary = [x for x in fit_results.values()]

        # Parsing the fit results to an overall result
        self.result.board_summary = self._run_summary(fit_results)

        # Shifting the results to the new configuration
        update_config = {}
        for channel in original_dacb_settings.keys():
            merge_nested(
                update_config,
                create_nested(
                    "roc_s0", "sc", "ch", channel, "Dacb", fit_results[channel][0]
                ),
            )
        tb_controller.i2c_socket.configure(update_config)

        # Saving the final results for data base reference, as well as the final
        # configuration used for data collection
        self.acquire_hgcroc(
            tbc=tb_controller,
            n_events=self.n_events,
            save_path="pedestal_final",
            desc="Final pedestal",
        )
        with self.open_text_file(
            path="pedestal_corrected_config.yaml", desc="final config"
        ) as f:
            f.write(yaml.dump(tb_controller.i2c_socket._config))

        return self.result

    def _run_scan(
        self,
        tb_controller: TBController,
        iterate: Callable,
        original_dacb_settings: Dict[str, int],
    ) -> Dict[str, Tuple[int, float, float]]:
        """
        Shifting the DACB results from the original values, returning the value
        of dictionary with the channels as key and the, shifted DACb setting,
        along with the pedestal mean and standard deviation.
        """
        scan_results = {channel: [] for channel in original_dacb_settings.keys()}
        for shift in iterate(
            range(self.lower_range, self.upper_range), desc="Shifting Dacb setting"
        ):
            # Creating the shifted results
            update_config = {}
            for channel, orig_val in original_dacb_settings.items():
                merge_nested(
                    update_config,
                    create_nested(
                        "roc_s0", "sc", "ch", channel, "Dacb", int(orig_val + shift)
                    ),
                )
            tb_controller.i2c_socket.configure(update_config)
            data = self.acquire_hgcroc(
                tb_controller,
                save_path=f"pedestal_shift{shift}.raw",
                desc="Initial readout from default configuration",
                dacb_shift=shift,
            )
            scan_array = rocv2.from_raw(self.full_path(data))

            for channel in original_dacb_settings.items():
                scan_results.append(
                    (
                        orig_val + shift,
                        numpy.mean(scan_array.adc[scan_array.channel == int(channel)]),
                        numpy.std(scan_array.adc[scan_array.channel == int(channel)]),
                    )
                )
        return scan_results

    def _run_fit(
        self,
        iterate: Callable,
        original_dacb_settings: Dict[str, int],
        scan_results: Dict[str, Tuple[int, float, float]],
    ) -> Dict[str, SingularResult]:
        """
        The SingularResult for each channel will also contain the recommended
        dacb setting for the final fitted result
        """

        def _lin_f(x, a, b):
            return a * x + b

        def _run_single_fit(orig, channel) -> SingularResult:
            # TODO, perform basic check on scan results
            try:
                x, y, ye = numpy.array(scan_results[channel]).T
                p, c = scipy.optimize.curve_fit(_lin_f, x, y, sigma=ye)
                opt = int(round((self.target_pedestal - p[1]) / p[0]))
            except Exception:
                return SingularResult(2, desc="FIT_FAILED", channel=channel, dacb=orig)

            if opt < orig + self.lower_range:
                return SingularResult(
                    1, desc="Fit out of range", channel=channel, dacb=orig
                )
            elif opt > orig + self.upper_range:
                return SingularResult(
                    1, desc="Fit out of range", channel=channel, dacb=orig
                )
            else:
                return SingularResult(0, desc="Success", channel=channel, dacb=opt)

        return {
            channel: _run_single_fit(orig, channel)
            for channel, orig in iterate(
                original_dacb_settings.items(), "Fitting scan results"
            )
        }

    def _run_summary(self, fit_results: Dict[str, SingularResult]) -> SingularResult:
        n_bad = numpy.sum(
            [(True if v.status != 0 else False) for v in fit_results.values()]
        )
        if n_bad > 0:
            return SingularResult(
                1, "Bad channels", channel=SingularResult.BOARD, n_bad=n_bad
            )
        else:
            return SingularResult(0, "Success", channel=SingularResult.BOARD)
