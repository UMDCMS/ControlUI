import collections

import numpy
import pyqtgraph
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...utils import get_datetime
from ..gui_session import GUISession
from ..qt_helper import _QContainer, _QLineEditDefault, _QRunButton, _QSpinBoxDefault


class _PortSpinBox(_QSpinBoxDefault):
    def __init__(self, default: int, *args, **kwargs):
        super().__init__(default, 1, 65536, *args, **kwargs)


class TBConnectionPanel(_QContainer):
    def __init__(self, session: GUISession):
        super().__init__(session)
        # Defining the basic layout
        self.box = QGroupBox("TBT connection", self)

        # Defining the inputs
        self.puller_ip_input = _QLineEditDefault("localhost", self)
        self.puller_port_input = _PortSpinBox(5555, self)
        self.control_ip_input = _QLineEditDefault("10.42.0.1", self)
        self.i2c_port_input = _PortSpinBox(6000, self)
        self.daq_port_input = _PortSpinBox(5000, self)

        # Connecting and disconnecting should be a "run button", as we should
        # not disconnect the tileboard when the something is running
        self.connect_button = _QRunButton(self.session, "Connect")
        self.disconnect_button = _QRunButton(self.session, "Disconnect")
        # Clearing setting should not be a "run button?"
        self.discard_button = QPushButton("Clear")

        # Telemetry plotting data
        self.update_timer = QTimer()
        self.time = collections.deque(maxlen=1024)
        self.tb_volt = collections.deque(maxlen=1024)
        self.canvas = pyqtgraph.PlotWidget()

        # Augmenting display based on current sessions status
        self.__init_layout__()
        self._display_update()
        self.connect_button.run_connect(self.tb_connect)
        self.discard_button.clicked.connect(self.tb_clear)
        self.disconnect_button.run_connect(self.tb_disconnect)
        self.update_timer.timeout.connect(self.update_plot_data)
        self.update_timer.start()

    def __init_layout__(self):
        self._box_outer = QVBoxLayout(self)
        self._box_inner = QVBoxLayout(self)

        self._form_layout = QFormLayout(self)
        self._form_layout.addRow("Puller IP", self.puller_ip_input)
        self._form_layout.addRow("Puller port", self.puller_port_input)
        self._form_layout.addRow("Controller IP", self.control_ip_input)
        self._form_layout.addRow("I2C port", self.i2c_port_input)
        self._form_layout.addRow("DAQ port", self.daq_port_input)
        self._box_inner.addLayout(self._form_layout)

        self._button_layout = QHBoxLayout(self)
        self.connect_button.setToolTip("Connect to new TB controller with settings")
        self.disconnect_button.setToolTip("Disconnect from connected TB controller")
        self.discard_button.setToolTip("Clear settings and show existing (or default)")
        self._button_layout.addWidget(self.connect_button)
        self._button_layout.addWidget(self.discard_button)
        self._button_layout.addWidget(self.disconnect_button)
        self._box_inner.addLayout(self._button_layout)

        # Additional container to limit the dimensions of the plot
        self._canvas_container = QWidget()
        self._canvas_container_layout = QVBoxLayout()
        self._canvas_container_layout.addWidget(self.canvas)
        self._canvas_container.setLayout(self._canvas_container_layout)
        self._canvas_container.setMaximumWidth(300)
        self._canvas_container.setMaximumHeight(300)
        self._box_inner.addWidget(self._canvas_container)
        # Additional setup For styling
        # self.canvas.setAxisItems({"bottom": pyqtgraph.DateAxisItem()})
        self._tb_volt_line = pyqtgraph.PlotDataItem(
            self.time, self.tb_volt, connect="finite"
        )
        self.canvas.addItem(self._tb_volt_line)
        self.canvas.setLabel("bottom", "Time ago [seconds]")
        self.canvas.setLabel("left", "Tileboard voltage")
        # Setting up the plot objects
        self.update_timer.setInterval(1000)

        self.box.setLayout(self._box_inner)
        self._box_outer.addWidget(self.box)
        self.setLayout(self._box_outer)

    @_QContainer.gui_action
    def tb_connect(self, event=None):
        # printing the form information
        print(
            "Puller@{0}:{1}".format(
                self.puller_ip_input.text(), int(self.puller_port_input.text())
            )
        )
        print(
            "TBC@{0}:{1}/{2}".format(
                self.control_ip_input.text(),
                self.i2c_port_input.text(),
                self.daq_port_input.text(),
            )
        )
        self.session.tb_controller = "CONNECTED!!"
        self._display_update()

    @_QContainer.gui_action
    def tb_clear(self, event=None):
        if self.session.tb_controller is None:
            pass
        else:
            pass
        self._display_update()

    @_QContainer.gui_action
    def tb_disconnect(self, event=None):
        self.session.tb_controller = None
        self._display_update()

    def _display_update(self, event=None):
        if self.session.tb_controller is None:
            self.box.setTitle("TBT connection (disconnected)")
            self.connect_button.session_config_valid = True
            self.disconnect_button.session_config_valid = False
        else:
            self.box.setTitle("TBT connection (connected!)")
            self.connect_button.session_config_valid = False
            self.disconnect_button.session_config_valid = True

    @_QContainer.gui_action
    def update_plot_data(self):
        now = get_datetime()
        self.time.append(now)
        self.tb_volt.append(
            numpy.random.normal(loc=10, scale=2)
            if self.session.tb_controller is not None
            else numpy.nan
        )

        self._tb_volt_line.setData(
            numpy.array([(now - x).total_seconds() for x in self.time]),
            numpy.array(self.tb_volt),
        )
