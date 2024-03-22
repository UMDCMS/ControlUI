import logging
import os

import qcmanager

# Initializing the logging sequence
logging.root.setLevel(logging.NOTSET)
logging.basicConfig(level=logging.NOTSET)

# Starting a blank session
session = qcmanager.session.Session()

# Loading the saved session
if os.path.exists("results/1234.5678"):
    session.load_yaml("results/1234.5678/session.yaml")
else:
    session.from_blank("1234", "5678")

# Loading hardware interfaces ###############################
# session.tb_controller = qcmanager.hw.TBController(
#    ip="10.42.0.1",
#    daq_port=6000,
#    pull_port=6001,
#    i2c_port=5555,
#    config_file="configure/tb_config_conv4.yml",
# )

# Running some instance #####################################
# session.handle_procedure(
#    qcmanager.procedures.pedestal_correction,
#    procedure_arguments=dict(
#        target_pedestal=70,
#        n_events=2000,
#    ),
# )
qcmanager.run_single_procedure(
    session,
    qcmanager.procedures.dummy_procedure,
    procedure_arguments=dict(target=70, pause=0.2),
)
qcmanager.run_single_procedure(
    session,
    qcmanager.procedures.dummy_process2,
    procedure_arguments=dict(pause=0.1, comp_file="mytest.txt"),
)

# Saving the session
session.save_session()
