"""
Collection of small of helper methods for data type casting and string parsing
"""


import collections
import datetime
import io
from typing import Any, Dict, Optional

import yaml


def _str_(s: str) -> str:
    """
    Converting a multiline string for code formatting to single line for
    in-built string formatters.
    """
    return " ".join(s.split())


def _to_dict(obj) -> Dict[str, Any]:
    """
    Casting a dataclass object to plain python dictionary representation.
    Object may have nested dataclass entries.
    """

    def convert_entry(entry):
        if isinstance(entry, str):
            return entry
        elif isinstance(entry, collections.abc.Mapping):
            return {k: convert_entry(v) for k, v in entry.items()}
        elif isinstance(entry, collections.abc.Iterable):
            # Always cast to list
            return list(convert_entry(x) for x in entry)
        elif hasattr(entry, "__dict__"):  # Handling nested entry
            return _to_dict(entry)
        else:  # Plain return
            return entry

    if isinstance(obj, collections.abc.Mapping):
        return {k: convert_entry(v) for k, v in obj.items()}
    else:
        return {k: convert_entry(v) for k, v in obj.__dict__.items()}


def to_yamls(obj) -> str:
    """Dumping object to yaml string"""
    return yaml.dump(_to_dict(obj), default_flow_style=False)


def to_yaml(obj, f: io.TextIOWrapper) -> None:
    """Writing object dictionary string to I/O pointer"""
    f.write(to_yamls(obj))


def get_datetime() -> datetime.datetime:
    """Return the current datetime item"""
    return datetime.datetime.now()


def timestamps(t: Optional[datetime.datetime] = None) -> str:
    """
    Returning time in standardized format. If no explicit datetime is given use
    the datetime.now() function.
    """
    t = get_datetime() if t is None else t
    return t.isoformat()


def timestampd(t: Optional[str] = None) -> datetime.datetime:
    """Returning a time stamp string as a datetime object"""
    t = get_datetime() if t is None else t
    return datetime.datetime.fromisoformat(t)


def timestampg(t: Optional[datetime.datetime | str] = None) -> str:
    """Returning time stamp string for GUI display"""
    t = get_datetime() if t is None else t
    t = timestampd(t) if isinstance(t, str) else t
    return t.strftime("%Y-%b-%d, %H:%M:%S")


def timestampf(t: Optional[datetime.datetime] = None) -> str:
    """
    Returning datetime to filename friendly format. Notice that this is not
    cannot convertable back to a datetime object, and is mainly aimed to avoid
    filename collisions.
    """
    return_string = timestamps(t)
    return_string = return_string.replace(":", "")
    return_string = return_string.replace(" ", "_")
    return return_string


"""
YAML options related functions
"""


def merge_nested(dest, update, path=None):
    """
    Updating a deeply nested dictionary-like object "dest" in-place using
    an update dictionary

    Updating the nested structure stored in the dictionary. The answer is
    adapted from this [answer][solution] on StackOverflow, except at because
    YAML configurations are not strictly dictionaries, we change the method of
    detecting nested structure to anything having the `__getitem__` method.

    [solution]:
    https://stackoverflow.com/questions/7204805/how-to-merge-dictionaries-of-dictionaries/7205107#7205107
    """
    if path is None:  # Leaving default argument as empty mutable is dangerous!
        path = []
    for key in update:
        if key in dest:
            dest_is_nested = hasattr(dest[key], "__getitem__")
            up_is_nested = hasattr(update[key], "__getitem__")
            if dest_is_nested and up_is_nested:
                # If both are nested recursively update nested structure
                merge_nested(dest[key], update[key], path + [str(key)])
            elif not dest_is_nested and not up_is_nested:
                # If neither are nested update value directory
                dest[key] = update[key]
            else:
                # Otherwise there is a structure mismatch
                raise ValueError(
                    "Mismatch structure at %s".format(".".join(path + [str(key)]))
                )
        else:
            dest[key] = update[key]
    return dest


def create_nested(*args):
    """
    Short hand function for making a deeply nested dictionary entry

    Nested dictionary entries are very verbose to declare in vanilla python,
    like  `{'a': {'b':{'c':{'d':v}}}}`, which is difficult to read and
    format using typical tools. This method takes arbitrary number of
    arguments, with all entries except for the last to be used as a key to a
    dictionary. So the example given above would be declared using this
    function as `create_nested('a','b','c','d', v)`
    """
    if len(args) == 1:
        return args[0]
    else:
        assert type(args[0]) is str, "Expect key to be of string type"
        return {args[0]: create_nested(*args[1:])}
