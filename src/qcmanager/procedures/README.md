# Defining procedures

All procedures must be defined as a direct inheritance of the
[`_procedure_base.ProcedureBase`](_procedure_base.py) class, and be decorated
with the [`dataclass(kw_only=True)`][dataclass] decorator. 

The non-hardware related requirements (which we will refer to as "procedure
arguments") are to be defined as the fields of the data class, and should be
annotated to indicate the data type, and default values (see below for more
details). The concrete values of procedure arguments will be accessible as
instance variable for the procedure.

The procedure execution should be defined by the `run` method, which takes in
the various required hardware interfaces as arguments. It is also recommended
to annotate these items with the appropriate types. In this run method, the
procedure arguments can be access as instances variables. Also in this run
method, you will have access to the `self.result` representing the calibration
results of this routine, as defined in the
[`ProcedureResults`](../yaml_format.py) class, which should be incrementally
updated as part of the procedure execution. Many bookkeeping entries for the
result are handled automatically, the following are key items that require
explicit parsing on the physicist side:

- `result.data_files`: A list of [`DataEntry`](../yaml_format.py), representing
  files that should be tracked as part of the result.
- `result.channel_summary`: A List of channel index, status code, and summary
  string container, named `SingularResult` used to represent the overall result
  of the procedure for a given channel. Arbitrary payloads that are of
  primitive python types can also be included to each `SingularResult` instance.
- `result.board_summary`: A "status code", and summary string used to represent
  the overall result of the procedure. The construction is the same as
  individual `SingularResult`, except that the channel should be set to the
  `SingularResult.BOARD` to indicate that this is not a channel result.


Some simplistic results of procedures can be found as the
[`dummy_process2.py`](dummy_process2.py) and the
[`dummy_procedure.py`](dummy_procedure.py) files.

One you have define a procedure, the simplest way to test the procedure
functions would be to write some custom scripts, as defined in the
[`example/`](../../../examples) directory. Though if you follow the
recommendations, the procedures will immediately be available in the main
methods.

[dataclass]: https://docs.python.org/3/library/dataclasses.html

## Some recommended patterns

### Annotating the arguments

For automatic methods for generating display elements and scripts to work, a
procedure class must defined with type annotates for both the procedure
arguments and the hardware interfaces. The main programs should raise an error
if you try and include a method without including the correct annotations.

For procedure arguments, it is required that you provide the type annotations
through the python [`typing.Annotated`][typing] method. The first argument
being the type you wish the argument to be (must be a python primitive type),
the second argument is the doc string describing what the argument will do, the
third argument will be additional parsing is useful to restraining the GUI
display elements used to display the arguments. This must be a custom classed
defined in the `_parsing.py` module file. Currently supported methods include:

- TBD


For hardware interfaces in the run function, these should all be simple typing
annotations. The master session class will automatically detect which hardware
interface to pass into the run call, which also generates an error for when the
hardware requirements are not met.

[typing]: https://docs.python.org/3/library/typing.html


### Looping/Iterating

When iterating over tasks, it is best-practice to process loops using a
"hardware-like" `iterate` interface. This will ensure that the loop progress
can be monitored by the user. This helps the user understand that something
might be taking a long time because it is processing over-multiple items, and
not that something has stalled. You can declare this looping interface by
annotated this with the the `_procedure_base.HWIterate` type indicator.

### Taking data

When taking data, it is best-practice to call the `self.acquire_hgcroc` method
or similar methods. This ensures that the data files will be stored in a
consistent directory structure, and will be tracked in the final result
container. Like-wise, if you want to write to a text file, and you wish for
this file to be tracked in the final result, use the `self.open_text_file`
method to obtain the file writer.

### Using previous result

If your procedure requires the use of the results obtained from other
procedures, request a `List[Procedure]` results item in the run argument. The
session manager will pass in its current results to the procedure runtime.
Helper functions for quickly obtaining the desired target result is currently
TBD.
