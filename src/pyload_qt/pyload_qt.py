
#!/usr/bin/env python3

import os
import signal
import sys

from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtGui import QIcon

from .pyload_client import PyLoadClient

from .ui.main import MainUIMixin
from .ui.packages import PackagesMixin
from .ui.package_actions import PackageActionsMixin
from .ui.bottom import BottomViewMixin
from .ui.links import LinksMixin
from .ui.downloads import DownloadsMixin
from .ui.files import FilesMixin
from .ui.session import SessionMixin


# class Object(object):
#      pass


class PyLoadUI(
        MainUIMixin,
        PackagesMixin,
        PackageActionsMixin,
        BottomViewMixin,
        LinksMixin,
        DownloadsMixin,
        FilesMixin,
        SessionMixin,
        QMainWindow,
    ):
    def __init__(self):
        super().__init__()

        self.client = PyLoadClient()
        self.current_package = None
        self.selected_package_pid = None
        self.package_files_subdir = ""
        self.config = {}

        self._debug_remove_links = False
        self._debug_package_data = False

        self.refresh_interval = 5

        self.init_ui()
        self.init_refresh_timer()
        self.login()


def main():
    # handle Ctrl+C from terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    window = PyLoadUI()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
