from typing import Tuple

from PyQt5.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

from . import gui_session, hwpanels, qt_helper, session_browser


def create_default_window() -> Tuple[QMainWindow, gui_session.GUISession]:
    session = gui_session.GUISession()

    # Creating the various containers
    session.tb_panel = hwpanels.tbconnection.TBConnectionPanel(session)
    session.temp_panel = hwpanels.temp_sensor.TempSensorPanel(session)
    session.loader = session_browser.SessionLoader(session)
    session.procedures = session_browser.SessionProcedureDisplay(session)
    session.singlerun = session_browser.SessionRunSingleProcedure(session)
    session.message_container = session_browser.SessionMessageDisplay(session)

    # Defining the layout
    session._hw_layout = QVBoxLayout()
    session._hw_layout.addWidget(session.tb_panel)
    session._hw_layout.addWidget(session.temp_panel)
    session._hw_layout.addStretch()
    session._hw_layout.setContentsMargins(0, 0, 0, 0)

    session._ses_layout = QVBoxLayout()
    session._ses_layout.addWidget(session.loader)
    session._ses_layout.addWidget(session.procedures)
    session._ses_layout.addWidget(session.singlerun)
    session._ses_layout.addWidget(session.message_container)
    session._ses_layout.addStretch()
    session._ses_layout.setContentsMargins(0, 0, 0, 0)

    session._outer_layout = QHBoxLayout()
    session._outer_layout.addLayout(session._hw_layout, stretch=0)
    session._outer_layout.addLayout(session._ses_layout, stretch=3)
    session._outer_layout.setContentsMargins(0, 0, 0, 0)
    session.setLayout(session._outer_layout)

    # Setting up the main window to be returned
    window = QMainWindow()
    window.setCentralWidget(session)

    # Setting up the master layout methods
    window.setWindowTitle("SiPM-on-tileboard QA/QC control")
    window.setGeometry(1600, 1000, 1600, 1000)
    session.refresh_signal.emit()

    return window, session
