from PyQt5.QtWidgets import QGroupBox, QVBoxLayout

from ..gui_session import GUISession
from ..qt_helper import _QContainer, _QRunButton


class TempSensorPanel(_QContainer):
    def __init__(self, session: GUISession):
        super().__init__(session)

        self._outer = QVBoxLayout()
        self._box = QGroupBox("Temperature Sensors")
        self._box_layout = QVBoxLayout()
        for i in range(1, 6):
            self._box_layout.addWidget(_QRunButton(self.session, f"Button {i}"))
        self._box.setLayout(self._box_layout)
        self._outer.addWidget(self._box)
        self.setLayout(self._outer)
