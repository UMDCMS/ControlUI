from PyQt5.QtWidgets import QGroupBox, QPushButton, QVBoxLayout

from ..gui_session import _QContainer, _QRunButton


class TempSensorPanel(_QContainer):
    def __init__(self, session):
        super().__init__(session)

        self._outer = QVBoxLayout(self)
        self._box = QGroupBox("Temperature Sensors", self)
        self._box_layout = QVBoxLayout(self)
        for i in range(1, 6):
            self._box_layout.addWidget(_QRunButton(self.session, f"Button {i}"))
        self._box.setLayout(self._box_layout)
        self._outer.addWidget(self._box)
        self.setLayout(self._outer)
