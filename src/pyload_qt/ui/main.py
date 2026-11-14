import os

from PySide6.QtCore import (
    Qt,
    QTimer,
)
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QPlainTextEdit,
    QSplitter,
    QHeaderView,
    QMessageBox,
    QDialog,
    QMenu,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QAbstractItemView,
    QButtonGroup,
    QStackedWidget,
    QSizePolicy,
)
from PySide6.QtGui import (
    QIcon,
    # QClipboard,
    # QPainter,
    QAction,
    QKeySequence,
    QFont,
)

from .rotate_label import RotateLabel
from .transfer_list_filters_widget import TransferListFiltersWidget
from .add_package_dialog import AddPackageDialog
from .app_settings import AppSettingsDialog


class MainUIMixin:

    def init_ui(self):
        self.setWindowTitle("pyLoad")
        self.setGeometry(100, 100, 1280, 720)
        self.setWindowIcon(QIcon(os.path.dirname(__file__) + "/pyload-logo.png"))

        # - root_widget: parent
        #   - sidebar_widget: sidebar
        #   - main_widget: main content
        # https://stackoverflow.com/a/56086494/10440128

        # root widget
        root_widget = QWidget()
        self.setCentralWidget(root_widget)
        root_layout = QHBoxLayout(root_widget)
        # root_widget.setLayout(root_layout)

        splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(splitter)

        self.main_widget = self.create_main_widget()
        self.packages_table.set_status_filter = lambda id: print("main_widget.set_status_filter", id)
        self.packages_table.set_status_filter = self.packages_table_set_status_filter
        # we need self.packages_table for self.sidebar_widget
        self.sidebar_widget = self.create_sidebar_widget()

        splitter.addWidget(self.sidebar_widget)
        splitter.addWidget(self.main_widget)

        splitter.setSizes([40, 200])
        # https://github.com/qbittorrent/qBittorrent/blob/feacfb062794f6fef00345ba704325a518ee6e5f/src/gui/mainwindow.cpp#L1366C1-L1368C1
        # splitter.setStretchFactor(0, 0)
        # splitter.setStretchFactor(1, 1)

    def create_sidebar_widget(self):
        # https://github.com/qbittorrent/qBittorrent/blob/master/src/gui/transferlistfilterswidget.cpp
        return TransferListFiltersWidget(self, self.packages_table)

    def create_main_widget(self):
        # Main widget and layout
        main_widget = QWidget()
        # self.setCentralWidget(main_widget) # -> root_widget
        main_layout = QVBoxLayout(main_widget)

        self.create_menu()

        self.create_toolbar()

        self.packages_table = self.create_packages_table()

        self.package_links_table = None

        # Splitter for tables
        splitter = QSplitter(Qt.Vertical)

        # Add widgets to main layout
        main_layout.addWidget(splitter)

        self.bottom_view_names = [
            "Package",
            "Links",
            "Downloads",
            "Files",
        ]

        self.default_bottom_view_name = "Downloads"
        self.default_bottom_view_idx = self.bottom_view_names.index(self.default_bottom_view_name)

        self.create_bottom_view_button_group(main_layout)
        self.bottom_view = self.create_bottom_view()

        splitter.addWidget(self.packages_table)
        splitter.addWidget(self.bottom_view)
        splitter.setSizes([300, 200])

        return main_widget

    def create_menu(self):
        self.menu = self.menuBar()

        file_menu = self.menu.addMenu("&File") # shortcut: Alt+F

        add_package_action = file_menu.addAction("Add Package")
        add_package_action.triggered.connect(self.show_add_package_dialog)
        add_package_action.setShortcut(QKeySequence.Open) # shortcut: Ctrl+O

        """
        refresh_action = file_menu.addAction("Refresh")
        refresh_action.triggered.connect(self.refresh_queue)
        """

        quit_action = file_menu.addAction("Quit")
        quit_action.triggered.connect(self.close)
        quit_action.setShortcut(QKeySequence.Quit) # shortcut: Ctrl+Q

    def create_toolbar(self):
        self.toolbar = self.addToolBar("Tools")

        start_icon = self.style().standardIcon(QStyle.SP_MediaPlay)
        start_action = QAction(start_icon, "Start downloads", self)
        start_action.triggered.connect(self.start_downloads)
        self.toolbar.addAction(start_action)

        pause_icon = self.style().standardIcon(QStyle.SP_MediaPause)
        pause_action = QAction(pause_icon, "Pause downloads", self)
        pause_action.triggered.connect(self.pause_downloads)
        self.toolbar.addAction(pause_action)

        stop_icon = self.style().standardIcon(QStyle.SP_MediaStop)
        stop_action = QAction(stop_icon, "Stop downloads", self)
        stop_action.triggered.connect(self.stop_downloads)
        self.toolbar.addAction(stop_action)

        """
        add_icon = QIcon(os.path.dirname(__file__) + "/img/plus-svgrepo-com.svg")
        add_action = QAction(add_icon, "Add Package", self)
        add_action.triggered.connect(self.show_add_package_dialog)
        self.toolbar.addAction(add_action)
        """

        def add_text_button(
                label,
                tooltip,
                action,
                size=25,
                bold=False,
                rotate=0,
                translate=(0, 0),
            ):
            # https://stackoverflow.com/a/79735780/10440128
            button = QToolButton()
            _action = QAction()
            _action.setToolTip(tooltip)
            _action.triggered.connect(action)
            button.setDefaultAction(_action)
            layout = QVBoxLayout(button)
            if rotate == 0:
                _label = QLabel(label)
            else:
                _label = RotateLabel(label, rotate=rotate, translate=translate)
            font_weight = QFont.Bold if bold else QFont.Normal
            font = QFont("Arial", size, font_weight)
            _label.setFont(font)
            layout.addWidget(_label, 0, Qt.AlignCenter)
            self.toolbar.addWidget(button)

        # plus symbol
        add_text_button("+", "Add Package", self.show_add_package_dialog, 25, True)

        # trash symbol = Wastebasket
        add_text_button("🗑", "Remove Finished", self.remove_finished, 14)

        # restart symbol = Anticlockwise Open Circle Arrow
        add_text_button("↺", "Restart Failed", self.restart_failed, 18)

        # Left-Pointing Double Angle Quotation Mark
        add_text_button("«", "Move to top", self.move_packages_to_top, 25, rotate=90, translate=(0, -5))

        # Broom emoji - no, too much color
        # add_text_button("🧹", "Remove unfinished links", self.remove_unfinished_links, 18)
        # "funnel" symbol https://stackoverflow.com/questions/37991395
        add_text_button("Y", "Remove unfinished links", self.remove_unfinished_links, 16)

        # Gear symbol = app settings
        add_text_button("⚙", "Settings", self.show_app_settings, 19)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        # https://gist.github.com/chipolux/a600d2a31b6811d553651822f89c9e39
        # pyqt debounced text input
        self.package_filter_input = QLineEdit()
        self.package_filter_input.setClearButtonEnabled(True)
        self.package_filter_input.setToolTip("Regex for Package names")
        self.package_filter_debounce = QTimer()
        self.package_filter_debounce.setInterval(1000)
        self.package_filter_debounce.setSingleShot(True)
        self.package_filter_debounce.timeout.connect(self.on_package_filter_change)
        self.package_filter_input.textChanged.connect(self.package_filter_debounce.start)
        self.toolbar.addWidget(self.package_filter_input)

    def show_app_settings(self):
        # print("show_app_settings")
        dialog = AppSettingsDialog(self)
        dialog.setModal(True)
        dialog.exec()

    def show_add_package_dialog(self):
        dialog = AddPackageDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, links, password = dialog.get_package_data()
            if not name:
                # local time with milliseconds and timezone
                # https://stackoverflow.com/questions/7588511
                name = datetime.datetime.now(datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo).isoformat(timespec='milliseconds')
            if not links:
                QMessageBox.warning(self, "Error", "No valid links found")
                return

            if password:
                def on_package_added(pid):
                    print(f"on_package_added {pid} -> calling set_package_data")
                    package_data = dict(password=password)
                    def on_set_package_data(res):
                        # TODO check res for errors
                        self.on_package_added(pid)
                    self.client.set_package_data(
                        on_set_package_data,
                        package_id=pid,
                        data=package_data
                    )
                pid = self.client.add_package(on_package_added, name=name, links=links)
            else:
                self.client.add_package(self.on_package_added, name=name, links=links)

    def add_package(self):
        name = self.package_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Package name cannot be empty")
            return

        links_text = self.links_input.toPlainText().strip()
        if not links_text:
            QMessageBox.warning(self, "Error", "No links provided")
            return

        # Extract URLs from text
        url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
        links = url_pattern.findall(links_text)

        if not links:
            QMessageBox.warning(self, "Error", "No valid links found")
            return

        self.client.add_package(self.on_package_added, name=name, links=links)

    def on_package_added(self, pid):
        if pid:
            # QMessageBox.information(self, "Success", "Package added successfully")
            self.refresh_queue()
        else:
            QMessageBox.warning(self, "Error", "Failed to add package")
