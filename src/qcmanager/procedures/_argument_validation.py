import fnmatch
import glob
from typing import List


class ArgumentValueChecker:
    """
    Base class for setting the number of limiting the solution
    """

    def __init__(self):
        self.session = None

    def _check_valid(self, argument) -> bool:
        return True


class Range(ArgumentValueChecker):
    def __init__(self, min_val, max_val):
        super().__init__()
        assert min_val < max_val
        self.min_val = min_val
        self.max_val = max_val

    def _check_valid(self, argument):
        return self.min_val <= argument <= self.max_val

    def __repr__(self):
        return f"Range({self.min_val}, {self.max_val})"


class StringListChecker(ArgumentValueChecker):
    """
    Checking if the str, type string is contain in a list. This is a type that
    can be chained together with the or operator.
    """

    def __init__(self):
        super().__init__()
        self._next = None

    def _check_valid(self, argument) -> bool:
        if not isinstance(argument, str):
            return False
        if argument in self.valid_list:
            return True
        if self._next is not None:
            self._next.session = self.session
            return self._next._check_valid(argument)
        return False

    @property
    def valid_list(self):
        return []

    @property
    def _full_list(self):
        if self._next is None:
            return self.valid_list
        else:
            return self._next._full_list + self.valid_list

    def __or__(self, other):
        assert isinstance(other, StringListChecker)
        other._next = self
        return other


class StrChoices(StringListChecker):
    """
    Checking if there is a valid list
    """

    def __init__(self, str_list: List[str]):
        super().__init__()
        self._str_list = str_list

    @property
    def valid_list(self):
        return self._str_list


class GlobChoices(StringListChecker):
    def __init__(self, glob_pattern):
        super().__init__()
        self.glob_pattern = glob_pattern

    @property
    def valid_list(self):
        return glob.glob(self.glob_pattern)


class ProcedureDataFiles(StringListChecker):

    def __init__(self, procedure_name: str, file_pattern: str):
        super().__init__()
        self.procedure_name = procedure_name
        self.file_pattern = file_pattern

    @property
    def valid_list(self):
        if self.session is None:
            return []
        else:
            data_path = []
            for result in self.session.results:
                if result.name != self.procedure_name:
                    continue
                data_path.extend(
                    [
                        data.path
                        for data in result.data_files
                        if fnmatch.fnmatch(data.path, self.file_pattern)
                    ]
                )
            data_path = [self.session.modify_save_path(x) for x in data_path]
            return data_path
