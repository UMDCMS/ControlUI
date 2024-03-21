"""
Pure data-container objects used to store the session results. All stored items
should be primitive types: ints, float, strings, lists, and dictionaries of
primitive types containing. Additional helper functions can be used to case
primitive types to be a program friendly data type.
"""

import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .utils import timestampd, timestamps


class DataEntry:
    """
    Data entry for a collected file. It must contain a path, a description, and
    a time stamp string (defaults to the time of creation). All other keyword
    arguments will be set as named attributes.
    """

    def __init__(self, path: str, desc: str, **kwargs):
        self.path: str = path
        self.desc: str = desc
        kwargs.setdefault("timestamp", timestamps())
        # All other items are passed as direct attributes
        for k, v in kwargs.items():
            setattr(self, k, v)


class SingularResult:
    """
    Singular results for either a single channel or a summary of the board.
    Each single result requires at least a status code and a description
    string, all other keyword arguments will be used to store the results
    """

    BOARD = -999  # Dummy channel results set for board status

    def __init__(self, status: int, desc: str, channel: int, **kwargs):
        self.status: int = status
        self.desc: str = desc
        self.channel: int = channel
        for k, v in kwargs.items():
            setattr(self, k, v)


@dataclass
class ProcedureResult:
    # Items to be automatically generated
    name: str
    _start_time: str
    _end_time: str
    input: Dict[str, Any]
    status_code: Tuple[int, str]  # Logical execution status

    # List of files that are produced by the procedure to be tracked either for
    # plotting or for later procedures.
    data_files: List[DataEntry] = field(default_factory=lambda: [])

    # Summary the overall board status of the overall procedure
    board_summary: Optional[SingularResult] = None

    # Summary results of each of the channel results
    channel_summary: List[SingularResult] = field(default_factory=lambda: [])

    @classmethod
    def from_dict(cls, d: dict):
        """
        Construction fron a dictionary object, required additional
        modification for the class-based storage
        """
        d["data_files"] = [DataEntry(**x) for x in d["data_files"]]
        d["board_summary"] = (
            SingularResult(**d["board_summary"])
            if d["board_summary"] is not None
            else None
        )
        d["channel_summary"] = [SingularResult(**x) for x in d["channel_summary"]]

        return ProcedureResult(**d)

    @property
    def start_time(self) -> datetime.datetime:
        """Returning datetime object for in-memory time comparisons"""
        return timestampd(self._start_time)

    @property
    def end_time(self) -> datetime.datetime:
        return timestampd(self._end_time)

    @property
    def last_data(self) -> DataEntry:
        return self.data_files[-1]

    @property
    def is_valid(self) -> bool:
        """Simple boolean flag for whether the execution was successful"""
        if self.status_code[0] != 0:
            return False
        if self.board_summary is None:
            return False
        return self.board_summary.status == 0
