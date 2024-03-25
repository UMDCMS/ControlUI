import time
from dataclasses import dataclass
from typing import Annotated, Callable, List, Tuple

import numpy
import scipy

from ..utils import timestamps
from ..yaml_format import DataEntry, ProcedureResult, SingularResult
from ._argument_validation import ProcedureDataFiles, Range
from ._procedure_base import HWIterable, ProcedureBase


@dataclass(kw_only=True)
class dummy_process2(ProcedureBase):
    """
    Dummy procedure for testing. Notice that doc strings will be used to
    generate helper documentation!
    """

    outer_size: Annotated[int, "Size of outer loop", Range(5, 10)] = 5
    inner_size: Annotated[int, "Size of inner loop", Range(5, 10)] = 10
    pause: Annotated[float, "Time between loops", Range(0.01, 1)] = 0.01
    comp_file: Annotated[
        str,
        "File to pull contents from",
        ProcedureDataFiles("dummy_procedure", "*.npy"),
    ]

    def run(
        self, iterate: HWIterable, session_log: List[ProcedureResult]
    ) -> ProcedureResult:
        """
        Example procedure mimicing a pedestal normalization routine with dummy
        inputs.
        """
        self.loginfo(f"Loading previous content: {len(numpy.load(self.comp_file))}")

        for _ in iterate(range(self.outer_size), desc="Outer Looping"):
            self.loginfo(f"Logging once per outer ({_ +1 })")
            for __ in iterate(range(self.inner_size), desc="Inner loop"):
                time.sleep(self.pause)

        with self.open_text_file("mytest.txt", desc="Just for demonstration") as f:
            f.write("I want this to be written")

        self.result.channel_summary = [
            SingularResult(0, "SUCESS", channel=c) for c in range(72)
        ]
        self.result.board_summary = SingularResult(
            0, "SUCCESS", channel=SingularResult.BOARD
        )
        return self.result
