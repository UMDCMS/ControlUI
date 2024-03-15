from PyQt5.QtWidgets import QVBoxLayout

from ..gui_session import GUISession, _QContainer
from .procedure_display import SessionProcedureDisplay
from .procedure_single import SessionRunSingleProcedure
from .session_loading import SessionLoader


class SessionBrowserContainer(_QContainer):
    def __init__(self, session: GUISession):
        super().__init__(session)

        self._outer = QVBoxLayout()
        self._loader = SessionLoader(self.session)
        self._procedures = SessionProcedureDisplay(self.session)
        self._singlerun = SessionRunSingleProcedure(self.session)
        self._outer.addWidget(self._loader)
        self._outer.addWidget(self._procedures)
        self._outer.addWidget(self._singlerun)
        self._outer.addWidget(self.session.monitor_box)
        self._outer.addStretch()

        self.setLayout(self._outer)
