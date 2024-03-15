# Creating a plotting method

For each of the procedures defined in the main `procedures` directory, you can
include a plotting file to have plot automatically be included in the GUI
display window. The functions must be declared in a class with a name name
matching the procedure name of interest.

All function declared with the `fig_` prefix will be consider part of GUI-level
plots, and these function should take in just a `ProcedureResult` instance and
return a singular `matplotlib.Figure` instance. Example plotting classes can be
found in the `dummy_procedure` and `dummy_process2` example file.

One defined, it is easiest to test out the plotting scripts using the
`bin/run_plotter` executable to plot a set of plots for a procedure stored in a
yaml file

## Best practice results

### Data file paths

When accessing data files via the `DataEntry` list of the procedure results,
its is best to use the `self.get_data_path` method, as this ensures that the
path is fully determined.

### Additional helper functions

For busy plots, like a display for multiple channels, it would be best if you
wrap everything in a the `create_interactive_legends` method, so the users can
choose which elements to display in the final GUI.
