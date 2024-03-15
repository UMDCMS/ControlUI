# Code base structure overview

## Persistent YAML representation of the session file

To ensure that the results of the calibration procedure persists after the
hardware and software shutdowns, calibration procedure results are represented
as a YAML file which is stored locally and updated on the termination of
calibration procedures. 

The management of the session is centrally done by a [`Session`](session.py)
instance, who stores the full record of procedure results, as well as the
in-memory references to the various hardware interfaces. Each procedure routine
is defined as a class, for each a new instance is created by each user request,
where the Session then pass the required hardware interfaces to the procedure
run method. During run time, each procedure instance will have be assigned a
`ProcedureResult` which should be incrementally updated following the procedure
logic, storing the files and results that would be useful for the QA/QC
procedure. The Session will automatically parse this and update the
corresponding YAML file once the procedure has is terminated.

For a brief overview of implementing a procedure, along with best practices,
see the documentation found in the [`procedures`](procedures) directory. 

## A GUI representation of the procedure results

During production, the full QA/QC procedure should be performed using the GUI,
to ensure that consistency is maintained, while also providing immediate visual
feedback for what might be causing issues. The visual representation of each
procedure result can be defined by a list of function in a corresponding file
in the [`plotting`](plotting) directory. See the documentation there for an
overview of implementing the plotting result a procedure routine.

## Defining the GUI interface

The GUI display elements are define in the [`qt_gui`](qt_gui) directory. If you
are following [best](procedures) [practices](plotting), the controls for newly
defined procedures and their corresponding plotting results should appear
automatically without having modify this directory. Contact the core developers
if you thing there is something missing.

## Defining new hardware interfaces 

Python interfaces to hardware controls, as well as the formatting and parsing
of their outputs are defined in the [`hw`](directory). Notice that hardware
interfaces are not automatically handled to be available to the primary
`Session` class, so you will need to consult with the core developers to have
new hardware included.
