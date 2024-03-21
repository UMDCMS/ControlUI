# Helper methods to interact with the solution
import os
from typing import List

import awkward

from ..hw import rocv2
from ..yaml_format import DataEntry


def get_hgcroc_array(data_list: List[DataEntry], store_base: str = "") -> awkward.Array:
    """
    Returning the obtained raw data files as a awkward array. The additional
    common metadata store in each DataEntry fields will be added as new
    event-level variable. And additional that will always be constructed will
    be the run_index, which is the order by which they appear in the data_list
    """
    array = []
    extra_fields = _get_extra_field_names(data_list)

    for index, entry in enumerate(data_list):
        sub_array = rocv2.from_raw(os.path.join(store_base, entry.path))
        sub_array["run_index"] = awkward.ones_like(sub_array.event) * index
        for field in extra_fields:
            sub_array[field] = awkward.ones_like(sub_array.event) * getattr(
                entry, field, None
            )
        array.append(sub_array)

    return awkward.concatenate(array, axis=0)


def _get_extra_field_names(data_list: List[DataEntry]) -> List[str]:
    field_names = []
    for entry in data_list:
        field_names.extend(
            [
                x
                for x in entry.__dict__.keys()
                if x != "path" and x != "desc" and x != "timestamp"
            ]
        )
    return list(set(field_names))
