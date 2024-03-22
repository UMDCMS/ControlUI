import time
from dataclasses import dataclass
from typing import Annotated, Callable, List, Tuple

import numpy
import scipy

from ..utils import timestamps
from ..yaml_format import DataEntry, ProcedureResult, SingularResult
from ._argument_validation import Range
from ._procedure_base import HWIterable, ProcedureBase


@dataclass(kw_only=True)
class dummy_procedure(ProcedureBase):
    """
    Dummy procedure for testing. Notice that doc strings will be used to
    generate helper documentation!
    """

    # Procedure (non-interface) arguments. Must declared with the Annotated
    # type hinting. The first value is the type, and should be a python
    # primitive type; the second is a string documenting the what the argument
    # does, and will be used to generate interface elements; the third is
    # optional which is indications for additional parsing.
    target: Annotated[int, "Target normalization value"]
    n_events: Annotated[int, "Number of events to collect"] = 200
    lower_range: Annotated[int, "Lower shift range", Range(-10, 0)] = -5
    upper_range: Annotated[int, "Upper shift range", Range(0, 10)] = 5
    pause: Annotated[float, "Time between DAQ calls (seconds)", Range(0.1, 2)] = 0.5

    # The main method that should be over-written by for each procedure of
    # interest. Here you should define the various hardware interfaces that you
    # use, the simple type annotation would be used to hint to the main session
    # manager which object to pass to the run call.
    def run(
        self, iterate: HWIterable, session_log: List[ProcedureResult]
    ) -> ProcedureResult:
        # Getting the concrete arguments types
        gen_type: int = len(session_log) % 3

        self.loginfo("Running initial scan with no shift")
        self._dummy_acquire(shift=0, save_file="dummy_initial.npy", gen_type=gen_type)
        self.result.last_data.desc = "Initial readout"

        # Making container for scan results
        self.loginfo("Running scan")
        scan_results = []
        for shift in iterate(
            range(self.lower_range, self.upper_range), desc="Shifting settings value"
        ):
            arr = self._dummy_acquire(
                shift=shift, save_file=f"dummy_shift{shift}.npy", gen_type=gen_type
            )
            scan_results.append(
                (
                    shift * numpy.ones_like(numpy.sum(arr, axis=-1)),
                    numpy.mean(arr, axis=-1),
                    numpy.std(arr, axis=-1),
                )
            )
            self.result.last_data.desc = f"shifted_readout_{shift}"
            time.sleep(self.pause)

        # Running the fit to obtain the best result
        self.loginfo("Running fit")
        self.result.channel_summary = self._run_fit(
            iterate=iterate,
            scan_results=scan_results,
        )

        # Parsing the fit results to an overall result
        self.loginfo("Generating summary")
        self.result.board_summary = self._run_summary(self.result.channel_summary)

        # Shifting the results to the new configuration
        self.loginfo("Saving final readout")
        self._dummy_acquire(shift=0, save_file="dummy_final.npy", gen_type=gen_type)
        self.result.last_data.desc = "Final_readout"
        return self.result

    def _dummy_acquire(self, shift, save_file: str, gen_type: int) -> numpy.ndarray:
        if gen_type % 3 == 0:
            arr = numpy.round(
                numpy.random.normal(
                    loc=85 - shift * 1.5, scale=2, size=(72, self.n_events)
                )
            )
        elif gen_type % 3 == 1:
            arr = numpy.round(
                numpy.random.normal(
                    loc=85 - shift * 1.5 - shift * shift * 0.5,
                    scale=2,
                    size=(72, self.n_events),
                )
            )
        elif gen_type % 3 == 2:
            arr = numpy.round(
                numpy.random.normal(
                    loc=85 - shift * 1.5 - shift * shift * 2,
                    scale=2,
                    size=(72, self.n_events),
                )
            )

        save_file = self.make_store_path(save_file)
        numpy.save(save_file, arr)
        self.result.data_files.append(
            DataEntry(path=save_file, desc="", timestamp=timestamps(), shift=shift)
        )
        return arr

    def _run_fit(
        self,
        iterate: Callable,
        scan_results: List[Tuple[int, float, float]],
    ) -> List[SingularResult]:
        """Each result would be the final result of the various items"""
        scan_results = numpy.array(scan_results)  # Casting to numpy array

        def _lin_f(x, a, b):
            return a * x + b

        def _run_single_fit(channel) -> SingularResult:
            x, y, ye = scan_results[:, :, channel].T
            try:
                p, c = scipy.optimize.curve_fit(_lin_f, x, y, sigma=ye)
                p = [float(x) for x in p]  # Casting to plain values
            except Exception:
                return SingularResult(
                    2,
                    "FIT FAILED",
                    channel=channel,
                    shift=0,
                    fit_param=(numpy.nan, numpy.nan),
                )
            opt = int(round((self.target - p[1]) / p[0]))
            if opt > self.upper_range or opt < self.lower_range:
                return SingularResult(
                    2, "OUT OF RANGE", channel=channel, shift=0, fit_param=(p[0], p[1])
                )
            return SingularResult(
                0, "SUCCESS", channel=channel, shift=opt, fit_param=(p[0], p[1])
            )

        return [
            _run_single_fit(x)
            for x in iterate(range(72), desc="Running fit on channels")
        ]

    def _run_summary(self, fit_results):
        none_zero = [i for i, x in enumerate(fit_results) if x.status != 0]
        if len(none_zero) != 0:
            return SingularResult(
                1, "HAS FAILED", channel=SingularResult.BOARD, fail_idx=none_zero
            )
        return SingularResult(0, "SUCCESS", channel=SingularResult.BOARD)
