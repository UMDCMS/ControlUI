import time
from dataclasses import dataclass
from typing import Annotated, Callable, List, Tuple

import numpy
import scipy

from ..utils import timestamps
from ..yaml_format import DataEntry, ProcedureResult, SingularResult
from ._procedure_base import HWIterable, ProcedureBase


@dataclass(kw_only=True)
class dummy_process2(ProcedureBase):
    """
    Dummy procedure for testing. Notice that doc strings will be used to
    generate helper documentation!
    """

    outer_size: Annotated[int, "Size of outer loop"] = 5
    inner_size: Annotated[int, "Size of inner loop"] = 10
    pause: Annotated[float, "Time between loops"] = 0.1

    def run(
        self,
        iterate: HWIterable,
        session_log: List[ProcedureResult],
    ) -> ProcedureResult:
        """
        Example procedure mimicing a pedestal normalization routine with dummy
        inputs.
        """
        for _ in iterate(range(self.outer_size), desc="Outer Looping"):
            self.loginfo(f"Logging once per outer ({_ +1 })")
            for __ in iterate(range(self.inner_size), desc="Inner loop"):
                time.sleep(self.pause)

        self.result.board_summary = SingularResult(
            0, "SUCCESS", channel=SingularResult.BOARD
        )
        self.result.channel_summary = [
            SingularResult(0, "SUCESS", channel=c) for c in range(72)
        ]
        return self.result
