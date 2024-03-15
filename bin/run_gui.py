import logging
import sys

from PyQt5.QtWidgets import QApplication

import qcmanager.qt_gui

if __name__ == "__main__":
    # Initializing the various items
    # Set the logger to log everything
    logging.root.setLevel(logging.NOTSET)
    logging.basicConfig(level=logging.NOTSET)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    # Do not run any parsing here
    app = QApplication([])
    # Here we initialize the main window
    window, session = qcmanager.qt_gui.create_default_window()

    window.show()
    sys.exit(app.exec_())
