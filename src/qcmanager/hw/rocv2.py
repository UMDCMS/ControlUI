"""
rocv2.py

High-level folding of the HGCROCv2RawData container into the format that is
suitable for fast online data processing using python/numpy/awkward.

In addition to the bit manipulation of the compact data words into human
readable columns, the functions here also folds the columns into the
appropriate form factors to allow for simple broad casting.
"""

import enum

import awkward
import uproot

from . import _rocv2  # For C++ data deserialization


class ChannelType(enum.IntEnum):
    """
    Enum for carrying indicating the channel type.
    """

    NORMAL = 0
    CALIBRATION = 1
    COMMON_MODE = 100  # This value is defined in runanalyzer.hpp in hexactrl-sw


@awkward.mixin_class(awkward.behavior)
class rocv2_behavior(awkward.Array):
    """
    Adding behavior to allow simpler data processing with less data mangling
    required to be written by the analyst. This includes following parts:

    - Expanding the per-half variables to effectively be per-channel (easier
      mapping of variables while keeping the data small).
    - Expanding the raw channel indices values to something that is easier to
      handle for the analysis (no overlap per event)
    - The addition of the channel type variable.
    """

    # Expanding per-half variables to behave like per-channel variables
    @property
    def corruption(self):
        return self._corruption[self.half]

    @property
    def bxcounter(self):
        return self._bxcounter[self.half]

    @property
    def eventcounter(self):
        return self._eventcounter[self.half]

    @property
    def orbitcounter(self):
        return self._orbitcounter[self.half]

    # Making the human readable channel index to unfold half
    # This is taken from
    @property
    def channeltype(self):
        ctype = ChannelType.NORMAL * awkward.ones_like(self.channel)
        ctype = awkward.where(self._channel == 36, ChannelType.CALIBRATION, ctype)
        ctype = awkward.where(self._channel > 36, ChannelType.COMMON_MODE, ctype)
        return ctype

    @property
    def channel(self):
        """
        Expanding the channels to a easier to use method. Channels from
        different HGCROC chip halves are assigned different values.
        """
        return self._channel + (numpy.max(self._channel) + 1) * self.half


awkward.behavior[".", "rocv2"] = rocv2_behavior  # Loading behavior


def from_raw(raw_file: str) -> awkward.Array:
    """
    Reading a raw data file, formatting into the columnar format, and perform the
    first level data mangling, as well as include the custom column behaviors.
    """
    container = _rocv2.rocv2(raw_file)
    n_entries = len(container.event())

    shape_dict = {
        # Per instance variables
        "event": None,
        "chip": None,
        "trigtime": None,
        "trigwidth": None,
        # Per half variables
        "corruption": container.nhalves,
        "bxcounter": container.nhalves,
        "eventcounter": container.nhalves,
        "orbitcounter": container.nhalves,
        # Per channel variables
        "half": container.nhalves * container.nchannels,
        "channel": container.nhalves * container.nchannels,
        "adc": container.nhalves * container.nchannels,
        "adcm": container.nhalves * container.nchannels,
        "tot": container.nhalves * container.nchannels,
        "toa": container.nhalves * container.nchannels,
        "totflag": container.nhalves * container.nchannels,
        # Trigger link
        "validtp": container.nlinks,
        "channelsumid": container.nlinks,
        "rawsum": container.nlinks,
        "decompresssum": container.nlinks,
    }

    def make_field_name(name):
        __hide_raw = [
            "corruption",
            "bxcounter",
            "eventcounter",
            "orbitcounter",
            "channel",
        ]
        if name in __hide_raw:
            return "_" + name
        else:
            return name

    def unflatten_array(name):
        size = shape_dict.get(name)
        if size is None:
            return awkward.from_numpy(getattr(container, name)())
        else:
            return awkward.from_regular(
                getattr(container, name)().reshape(n_entries, size)
            )

    # Returning the data pattern
    return awkward.Array(
        {make_field_name(name): unflatten_array(name) for name in shape_dict.keys()},
        with_name="rocv2",
    )


def save_root(array: awkward.Array, filename: str) -> None:
    """
    Saving the arrays to a root file.
    """
    with uproot.recreate(filename) as f:
        f["hgcrocv2"] = {f: array[f] for f in array.fields}


def from_root(filename: str) -> awkward.Array:
    """
    Loading root from arrays, also inject the required behavior
    """
    with uproot.open(filename) as f:
        return awkward.Array(f["hgcrocv2"].arrays(), with_name="rocv2")


def from_unpack(unpack_file: str) -> awkward.Array:
    """
    From unpacked.
    """
    raise NotImplementedError("Handling of unpack is still note done")
    pass
