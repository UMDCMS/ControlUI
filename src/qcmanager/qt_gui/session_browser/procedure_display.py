import importlib
from typing import List, Optional

import matplotlib.backends.backend_qt5agg
from PyQt5.QtCore import QAbstractTableModel, Qt
from PyQt5.QtWidgets import (
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ...utils import timestampg
from ...yaml_format import ProcedureResult, SingularResult
from ..gui_session import GUISession, _QContainer, clear_layout

# Aliases for simpler declaration
FigureCanvas = matplotlib.backends.backend_qt5agg.FigureCanvasQTAgg
NavigationToolbar = matplotlib.backends.backend_qt5agg.NavigationToolbar2QT


class MplCanvasWidget(QWidget):
    def __init__(self, figure):
        super().__init__()
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        self._canvas = FigureCanvas(figure)
        self._toolbar = NavigationToolbar(self._canvas)
        self._layout.addWidget(self._toolbar)
        self._layout.addWidget(self._canvas)


class SessionProcedureDisplay(_QContainer):
    def __init__(self, session: GUISession):
        super().__init__(session)

        self._outer = QVBoxLayout()
        self._box = QGroupBox("QA/QC Procedure results")
        self._inner = QHBoxLayout()
        self.setLayout(self._outer)
        self._outer.addWidget(self._box)
        self._box.setLayout(self._inner)

        self._detail_display = ProcedureDetailDisplay(self.session)
        self._list_display = ProcudureSummaryList(self.session, self._detail_display)
        self._inner.addWidget(self._list_display, stretch=1)
        self._inner.addWidget(self._detail_display, stretch=2)


class ProcedureDetailDisplay(_QContainer):
    def __init__(self, session: GUISession):
        super().__init__(session)

        self._outer = QVBoxLayout()
        self._box = QGroupBox("Detailed results")
        self._inner = QHBoxLayout()

        self._text_display_container = QVBoxLayout()
        self.text_display = QFormLayout()
        self._text_details_box = QGroupBox("Item details")
        self.text_details = QFormLayout()
        self._text_display_container.addLayout(self.text_display)
        self._text_display_container.addWidget(self._text_details_box)
        self._text_details_box.setLayout(self.text_details)
        self._plot_display_box = QGroupBox("Plots")
        self._plot_display_layout = QVBoxLayout()
        self._plot_display_box.setLayout(self._plot_display_layout)

        self._inner.addLayout(self._text_display_container)
        self._inner.addWidget(self._plot_display_box)

        self._box.setLayout(self._inner)
        self._outer.addWidget(self._box)
        self.setLayout(self._outer)

        # Special item storing the current display format
        self.result = None

        # Initial item
        self.display_result()

    def display_result(self, index: Optional[int] = None):
        if index is None:
            self.text_display.addWidget(QLabel("Select from left"))
            self._plot_display_layout.addWidget(QLabel("None selected"))
            self.text_details.addWidget(QLabel("None selected"))
        else:
            self.result = self.session.results[index]
            self.display_text_results()
            self.display_plot_results()

    @classmethod
    def make_brief_label(cls, r: SingularResult):
        return "{status}{message}".format(
            status="Good" if r.status else "Failed",
            message=f" ({r.desc})" if r.status != 0 else "",
        )

    def display_text_results(self):
        # Rebuilding all the major results
        clear_layout(self.text_display)
        # Updating the header
        self._box.setTitle(
            "Detailed results ({name}, completed {time})".format(
                name=self.result.name, time=timestampg(self.result.end_time)
            )
        )

        # Simple method for adding direct text:
        def _add_row(header: str, entry: str):
            self.text_display.addRow(header, QLabel(str(entry)))

        _add_row("Procedure name", self.result.name)
        _add_row(
            "Logical status",
            "{status} {message}".format(
                status="Complete" if self.result.status_code[0] == 0 else "Error",
                message=(
                    f"({self.result.status_code[1]})"
                    if self.result.status_code[0] != 0
                    else ""
                ),
            ),
        )
        _add_row("Start time", timestampg(self.result.start_time))
        _add_row("End time", timestampg(self.result.end_time))

        summary_label = QLabel(
            "<u>"
            + ProcedureDetailDisplay.make_brief_label(self.result.board_summary)
            + "</u>"
        )
        summary_label.mousePressEvent = self.display_details(
            "Board summary information", self.result.board_summary
        )
        self.text_display.addRow("Board summary", summary_label)

        # Per channel diagnostics
        per_channel = QGridLayout()
        for idx, channel in enumerate(self.result.channel_summary):
            channel_item = QLabel(str(idx))
            if channel.status != 0:
                channel_item.setStyleSheet("QLabel {background-color: red}")
            else:
                channel_item.setStyleSheet("QLabel {background-color: green}")
            channel_item.mousePressEvent = self.display_details(
                f"Information for channel {idx}", channel
            )
            per_channel.addWidget(channel_item, idx // 8, idx % 8)
        self.text_display.addRow("Per-channel summary", per_channel)

    def display_plot_results(self):
        clear_layout(self._plot_display_layout)
        try:
            plotlib = importlib.import_module(f"qcmanager.plotting.{self.result.name}")
        except Exception:
            self._plot_display_layout.addWidget(QLabel("No plotting methods found"))
            return

        plot_view = QTabWidget()
        plot_view.setMinimumWidth(800)
        plot_view.setMinimumHeight(500)
        plotter = getattr(plotlib, self.result.name)(self.session.save_base)

        for p_name, p_func in plotter.figure_methods.items():
            try:
                figure_widget = MplCanvasWidget(p_func(self.result))
            except Exception as err:
                figure_widget = QLabel(
                    "\n".join(
                        [
                            "Failed to generate plot",
                            f"Check function from plotting.{self.result.name}.fig_{p_name}",
                            f"Message: {str(err)}",
                        ]
                    )
                )
            finally:
                plot_view.addTab(figure_widget, p_name.replace("_", " "))
        self._plot_display_layout.addWidget(plot_view)

    def display_details(self, header: str, r: SingularResult):
        container = self

        def _update_text_details(self, event=None):
            clear_layout(container.text_details)
            container._text_details_box.setTitle(header)

            def _add_row(header: str, entry: str):
                entry_text = QLabel(entry)
                entry_text.setWordWrap(True)
                container.text_details.addRow(header, entry_text)

            _add_row("Summary code", str(r.status))
            _add_row("Summary description", r.desc)
            for k, v in r.__dict__.items():
                # Displaying all other items
                if k.startswith("_") or k == "status" or k == "desc":
                    continue
                _add_row(k, str(v))

        return _update_text_details


class ProcedureTableModel(QAbstractTableModel):
    def __init__(self, results_list: List[ProcedureResult]):
        super().__init__()
        self._data = results_list  # Getting refernce to main item

    def data(self, index, role):
        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self._data[index.row()].name
            if index.column() == 1:
                valid = self._data[index.row()].is_valid
                return "Good" if valid else "Failed"
            if index.column() == 2:
                return timestampg(self._data[index.row()].end_time)
            else:
                return ""
        if role == Qt.TextAlignmentRole:
            if index.column() != 2:
                return Qt.AlignHCenter | Qt.AlignVCenter
            else:
                return Qt.AlignVCenter

    def headerData(self, section, orientation, role):
        # section is the index of the column/row.
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if section == 0:
                    return "Name"
                if section == 1:
                    return "Result"
                if section == 2:
                    return "End time"
                return ""

            if orientation == Qt.Vertical:
                return ""

    def rowCount(self, index):
        return len(self._data)

    def columnCount(self, index):
        return 3


class ProcudureSummaryList(_QContainer):
    def __init__(self, session: GUISession, detail_view: ProcedureDetailDisplay):
        super().__init__(session)
        self._detail_view = detail_view

        self._outer = QVBoxLayout()
        self._box = QGroupBox("Overview")
        self._inner = QVBoxLayout()
        self.setLayout(self._outer)
        self._outer.addWidget(self._box)
        self._box.setLayout(self._inner)

        self._table_view = QTableView()
        self._inner.addWidget(self._table_view)
        self._display_update()

        # Setting up the logical behavior
        self._table_view.clicked.connect(self.display_detail)

    def _display_update(self):
        self._table_model = ProcedureTableModel(self.session.results)
        self._table_view.setModel(self._table_model)
        self._table_view.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

    def display_detail(self, item):
        self._detail_view.display_result(item.row())
