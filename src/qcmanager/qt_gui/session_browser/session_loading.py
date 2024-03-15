import glob
import os

import yaml
from PyQt5.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from ...utils import _str_
from ..gui_session import (
    GUISession,
    _QComboPlaceholder,
    _QConfirmationDialog,
    _QContainer,
    _QRunButton,
)


class SessionLoader(_QContainer):
    def __init__(self, session: GUISession):
        super().__init__(session)

        self.box = QGroupBox("Session", self)

        # Items for loading in a new session
        self.load_new_type_input = _QComboPlaceholder("-- choose board type --")
        self.load_new_id_input = QLineEdit()
        self.load_new_button = _QRunButton(session, "Load new")

        # Items for laoding in an existing session
        self.load_existing_input = _QComboPlaceholder("-- Choose existing --")
        self.load_existing_button = _QRunButton(session, "Load existing")

        # Items for current summary
        self.boardtype_label = QLabel("")  # Dynamic elements should be Widgets
        self.boardid_label = QLabel("")
        self.log_summary_label = QLabel("")
        self.update_label = QLabel("")

        # Input checking
        self.load_new_type_input.on_textchange(self.check_new_inputs)
        self.load_new_id_input.textChanged.connect(self.check_new_inputs)
        self.load_existing_input.on_textchange(self.check_existing_inputs)

        # Defining the run routines
        self.load_new_button.set_run(self.load_new)
        self.load_existing_button.set_run(self.load_existing)

        # General display update based on current session status
        self.__init_layout__()
        self._display_update()

    def __init_layout__(self):
        self._box_outer = QVBoxLayout()
        self._box_inner = QVBoxLayout()
        self._action_layout = QHBoxLayout()

        # Items for loading in a new session
        self._load_new_box = QGroupBox("Load new session")
        self._load_new_box_layout = QFormLayout()
        self._load_new_box_layout.addRow("Board type", self.load_new_type_input)
        self._load_new_box_layout.addRow("Board id", self.load_new_id_input)
        self._load_new_box_layout.addRow("", self.load_new_button)
        self._load_new_box.setLayout(self._load_new_box_layout)
        self._action_layout.addWidget(self._load_new_box, stretch=1)

        # Items for laoding in an existing session
        self._load_existing_box = QGroupBox("Load existing session")
        self._load_existing_box_layout = QFormLayout()
        self._load_existing_box_layout.addRow("Session file", self.load_existing_input)
        self._load_existing_box_layout.addRow("", self.load_existing_button)
        self._load_existing_box.setLayout(self._load_existing_box_layout)
        self._action_layout.addWidget(self._load_existing_box, stretch=1)

        # Items for current summary
        self._summary_layout = QHBoxLayout()
        self._summary_layout.addWidget(self.boardtype_label)
        self._summary_layout.addWidget(self.boardid_label)
        self._summary_layout.addWidget(self.log_summary_label)
        self._summary_layout.addWidget(self.update_label)

        self._box_inner.addLayout(self._action_layout)
        self._box_inner.addLayout(self._summary_layout)
        self.box.setLayout(self._box_inner)
        self._box_outer.addWidget(self.box)
        self.setLayout(self._box_outer)

    def _display_update(self):
        self._update_summary()
        self._update_templates()
        self._update_existing()

    def _update_summary(self):
        """Show basic information of currect session"""
        if self.session.board_id == "" or self.session.board_type == "":
            self.box.setTitle("Session (none loaded)")
            self.boardtype_label.setText("")
            self.boardid_label.setText("")
            self.log_summary_label.setText("")
            self.update_label.setText("")
            return
        self.box.setTitle(
            f"Session (loaded {self.session.board_type}@{self.session.board_id})"
        )
        self.boardtype_label.setText("<b>Board type: </b>" + self.session.board_type)
        self.boardid_label.setText("<b>Board ID: </b>" + self.session.board_id)
        # Procedure update
        total_run = len(self.session.results)
        success_run = len([x for x in self.session.results if x.is_valid])
        self.log_summary_label.setText(
            "<b>Procedure(s)</b> (Tot/S/F): "
            + f"{total_run}/{success_run}/{total_run-success_run}"
        )
        # Last entry update
        time_str = (
            "N/A"
            if len(self.session.results) == 0
            else self.session.results[-1].end_time.strftime("%Y-%b-%d (%a), %I:%M%p")
        )
        self.update_label.setText("<b>Last update:</b>" + time_str)

    def _update_templates(self):
        """Getting available template sessions"""
        self.load_new_type_input.clear()
        with open("configurations/tileboard_layouts.yaml", "r") as f:
            layout_list = sorted(yaml.safe_load(f))
        for f in layout_list:
            self.load_new_type_input.addItem(f)
        self.load_new_button.setDisabled(True)  # Disable by default

    def _update_existing(self):
        self.load_existing_input.clear()
        template_files = glob.glob("results/*")
        template_files = sorted([os.path.basename(x) for x in template_files])
        for f in template_files:
            self.load_existing_input.addItem(f)
        self.load_existing_button.setDisabled(True)  # Disable by default

    def check_new_inputs(self):
        new_type = self.load_new_type_input.currentText()
        new_id = self.load_new_id_input.text()

        def _is_valid_type():
            return bool(new_type in self.load_new_type_input.item_texts)

        def _is_valid_id():
            # TODO: More checks to perform for
            return bool(new_id)

        self.load_new_button.session_config_valid = _is_valid_type() and _is_valid_id()
        self.load_new_button._display_update()

    def check_existing_inputs(self):
        session_file = self.load_existing_input.currentText()

        def _is_valid_session():
            # TODO: More checks
            return bool(
                session_file and session_file in self.load_existing_input.item_texts
            )

        self.load_existing_button.session_config_valid = _is_valid_session()
        self.load_existing_button._display_update()

    @_QContainer.gui_action
    def load_new(self, action=False):
        board_type = self.load_new_type_input.currentText()
        board_id = self.load_new_id_input.text()

        def _load_blank():
            self.session.from_blank(board_type=board_type, board_id=board_id)
            self.session.refresh()

        if self._has_session():
            if self._confirm_load_session():
                _load_blank()
        else:
            _load_blank()

    @_QContainer.gui_action
    def load_existing(self, event=False):
        target = self.load_existing_input.currentText()
        target_yaml = f"{self.session.LOCAL_STORE}/{target}/session.yaml"

        def _load():
            self.session.load_yaml(target_yaml)
            self.session.refresh()

        # Do nothing if target session is already loaded
        if target == f"{self.session.board_type}.{self.session.board_id}":
            self.session.refresh()
            return

        if self._has_session():
            if self._confirm_load_session():
                _load()
        else:
            _load()

    def _has_session(self):
        return self.session.board_id != "" or self.session.board_type != ""

    def _confirm_load_session(self):
        _confirm_box = _QConfirmationDialog(
            parent=self.session,
            brief="Overwrite session?",
            full_message=_str_(
                "A session is already loaded, are you sure you want to exit?"
            ),
        )
        _confirm_box.setParent(self.session)
        return _confirm_box.exec()