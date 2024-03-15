from typing import Tuple

from PyQt5.QtWidgets import QHBoxLayout, QMainWindow, QVBoxLayout

from . import gui_session, hwpanels, session_browser


def create_default_window() -> Tuple[QMainWindow, gui_session.GUISession]:
    session = gui_session.GUISession()
    session.hw_column = gui_session._QContainer(session)
    session.tb_panel = hwpanels.tbconnection.TBConnectionPanel(session)
    session.temp_panel = hwpanels.temp_sensor.TempSensorPanel(session)
    session.hw_layout = QVBoxLayout()
    session.hw_layout.addWidget(session.tb_panel)
    session.hw_layout.addWidget(session.temp_panel)
    session.hw_column.setLayout(session.hw_layout)

    session.browse_column = session_browser.outer_container.SessionBrowserContainer(
        session
    )

    session.column_layout = QHBoxLayout()
    session.column_layout.addWidget(session.hw_column, stretch=0)
    session.column_layout.addWidget(session.browse_column, stretch=3)
    session.setLayout(session.column_layout)

    window = QMainWindow()
    window.setCentralWidget(session)

    # Setting up the master layout methods
    window.setWindowTitle("SiPM-on-tileboard QA/QC control")
    window.setGeometry(1600, 1000, 1600, 1000)
    session.refresh()

    return window, session
