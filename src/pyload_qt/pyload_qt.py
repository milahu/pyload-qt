#!/usr/bin/env python3

import os
import sys
import signal
import json
import re
import subprocess
import urllib.parse
import datetime
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
from PySide6.QtCore import Qt, QUrl
from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtGui import QIcon, QScreen
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtGui import QFont
from PySide6.QtGui import (
    QClipboard,
    QPainter,
)
NetworkError = QNetworkReply.NetworkError

from . import transferlistfilterswidget



class PyLoadClient:
    def __init__(self):
        self.manager = QNetworkAccessManager()
        # FIXME by default, the pyload server runs with ipv6
        # but with webui.develop=True in ~/.pyload/settings/pyload.cfg it runs with ipv4
        self.base_url = "http://localhost:8000" # ipv4: login fails with NetworkError.ConnectionRefusedError
        self.base_url = "http://127.0.0.1:8000" # ipv4: login fails with NetworkError.ConnectionRefusedError
        self.base_url = "http://[::1]:8000" # ipv6
        self.is_localhost = True
        self.session_cookie = None
        self.func_cache = {}

    # https://stackoverflow.com/questions/13194180/dynamic-method-generation-in-python
    def __getattr__(self, name):
        # print(f"getattr {name}")
        try:
            return self.func_cache[name]
        except KeyError:
            pass
        # print(f"creating function {name}")
        # def func(self, *args, **kwargs, callback): # ?
        # def func(self, *args, callback=None, **kwargs): # ?
        # def func(*args, callback=None, **kwargs): # ?
        # def func(self, callback, *args, **kwargs):
        def func(callback, *args, **kwargs):
            if name in ("status", "links"):
                api_dir = "json"
            else:
                api_dir = "api"
            if name in ("login",):
                # method = "post"
                is_get = False
            else:
                # method = "get"
                is_get = True
            url = f"{self.base_url}/{api_dir}/{name}"
            if args:
                url += "/" + ",".join(map(str, args))
            if kwargs and is_get:
                kwargs_json = dict()
                for key, val in kwargs.items():
                    kwargs_json[key] = json.dumps(val, separators=(",", ":"))
                url += "?" + urllib.parse.urlencode(kwargs_json)
            elif kwargs and not is_get:
                post_data = urllib.parse.urlencode(kwargs).encode()
            # print(f"client.{name}: url = {url!r}")
            request = QNetworkRequest(QUrl(url))
            if self.session_cookie:
                request.setRawHeader(b"Cookie", self.session_cookie.encode())
            if is_get:
                reply = self.manager.get(request)
            else:
                request.setHeader(
                    QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded"
                )
                reply = self.manager.post(request, post_data)
            def handle_reply():
                if reply.error() == QNetworkReply.NoError:
                    data = json.loads(reply.readAll().data().decode())
                    if callback: callback(data)
                else:
                    # TODO also print response body with the server exception
                    print(f"{name} reply.error", reply.error())
                    # consumers should check the result with
                    # isinstance(result, QNetworkReply.NetworkError)
                    if callback: callback(reply.error())
                reply.deleteLater()
            reply.finished.connect(handle_reply)
        func.__name__ = name
        self.func_cache[name] = func
        return func


class AddPackageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Package")
        self.setModal(True)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Package name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Package Name:"))
        self.package_name_input = QLineEdit()
        name_layout.addWidget(self.package_name_input)
        layout.addLayout(name_layout)

        # Links input
        layout.addWidget(QLabel("Links (one per line or space separated):"))
        self.links_input = QTextEdit()
        layout.addWidget(self.links_input)

        # Package password
        password_layout = QHBoxLayout()
        password_layout.addWidget(QLabel("Password:"))
        self.package_password_input = QLineEdit()
        password_layout.addWidget(self.package_password_input)
        layout.addLayout(password_layout)

        # Buttons
        button_layout = QHBoxLayout()
        self.add_button = QPushButton("Add Package")
        self.add_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

    def get_package_data(self):
        name = self.package_name_input.text().strip()
        links_text = self.links_input.toPlainText().strip()
        url_pattern = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
        links = url_pattern.findall(links_text)
        password = self.package_password_input.text().strip()
        return name, links, password


# https://stackoverflow.com/a/2304495/10440128
class SortKeyTableWidgetItem(QTableWidgetItem):
    def __init__(self, text, sortKey):
        #call custom constructor with UserType item type
        super().__init__(text, QTableWidgetItem.UserType)
        self.sortKey = sortKey

    #Qt uses a simple < check for sorting items, override this to use the sortKey
    def __lt__(self, other):
        return self.sortKey < other.sortKey


class Object(object):
     pass


# alternative: class RotateLabel(QLabel)
r"""
# FIXME this creates a black box
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsProxyWidget,
    QGraphicsView,
)
_label = QLabel(label)
font_weight = QFont.Bold if bold else QFont.Normal
font = QFont("Arial", size, font_weight)
_label.setFont(font)
# https://stackoverflow.com/search?q=%5Bpyside%5D+QGraphicsProxyWidget
# _label.setFixedSize(100, 40)
# https://www.qtcentre.org/threads/56742-how-to-make-transparent-qgraphicsproxywidget
# _label.setStyleSheet("background-color:transparent")
# _label.setAutoFillBackground(False)
# https://stackoverflow.com/a/11676527/10440128
scene = QGraphicsScene()
proxy = QGraphicsProxyWidget()
proxy.setWidget(_label)
scene.addItem(proxy)
# proxy.setPos(50, 50)
proxy.setRotation(rotate)
view = QGraphicsView(scene)
# view.setStyleSheet("background-color:transparent")
# view.setAutoFillBackground(False)
# https://stackoverflow.com/questions/60730190
_label.update()
_label.show()
view.show()
_label = view
"""


class RotateLabel(QLabel):
    # https://stackoverflow.com/a/70480783/10440128
    def __init__(self, *a, rotate=0, translate=(0, 0), **k):
        super().__init__(*a, **k)
        self.rotate = rotate
        self.translate = translate
    def paintEvent(self, e): # e: QPaintEvent
        painter = QPainter(self)
        painter.translate(self.rect().center())
        painter.rotate(self.rotate)
        painter.translate(-self.rect().center())
        if self.translate != (0, 0):
            painter.translate(*self.translate)
        painter.drawText(self.rect(), Qt.AlignHCenter | Qt.AlignVCenter, self.text())
        # QWidget.paintEvent(e)


class PyLoadUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client = PyLoadClient()
        self.current_package = None
        self.init_ui()
        self.login()
        self.refresh_interval = 5 # refresh every 5 seconds
        self.init_refresh_timer()
        self.selected_package_pid = None
        self.package_files_subdir = ""
        self._debug_remove_links = False
        self._debug_package_data = False

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

    def packages_table_set_status_filter(self, status_id):
        table = self.packages_table
        max_status_id = 5
        if not (0 <= status_id <= max_status_id):
            raise ValueError(f"bad status_id {status_id}")
        # FIXME this conflicts with on_package_filter_change
        if status_id == 0: # all
            for row_idx in range(table.rowCount()):
                table.setRowHidden(row_idx, False)
        else:
            for row_idx in range(table.rowCount()):
                package_queue_col_idx = 2 # Status: Queue or Collector
                package_progress_col_idx = 3 # Progress
                hidden = False
                if status_id in (1, 2):
                    package_queue = table.item(row_idx, package_queue_col_idx).data(Qt.UserRole)
                    if status_id == 1: # active aka "pyload queue"
                        hidden = not(package_queue)
                    elif status_id == 2: # paused aka "pyload collector"
                        hidden = package_queue
                if status_id in (3, 4, 5):
                    package_progress = table.item(row_idx, package_progress_col_idx).data(Qt.UserRole)
                    if status_id == 3: # complete
                        hidden = (package_progress < 1)
                    elif status_id == 4: # partial
                        hidden = (package_progress in (0, 1))
                    elif status_id == 5: # empty
                        hidden = (package_progress > 0)
                table.setRowHidden(row_idx, hidden)

    def create_sidebar_widget(self):
        # https://github.com/qbittorrent/qBittorrent/blob/master/src/gui/transferlistfilterswidget.cpp
        return transferlistfilterswidget.TransferListFiltersWidget(self, self.packages_table)

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
        add_text_button("«", "Move to top", self.move_package_to_top, 25, rotate=90, translate=(0, -5))

        # Broom emoji - no, too much color
        # add_text_button("🧹", "Remove unfinished links", self.remove_unfinished_links, 18)
        # "funnel" symbol https://stackoverflow.com/questions/37991395
        add_text_button("Y", "Remove unfinished links", self.remove_unfinished_links, 16)

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

    def on_package_filter_change(self):
        filter_text = self.package_filter_input.text().strip()
        print("on_package_filter_change", repr(filter_text))
        table = self.packages_table
        if not filter_text:
            # show all rows
            for row_idx in range(table.rowCount()):
                table.setRowHidden(row_idx, False)
        # https://stackoverflow.com/a/6785516/10440128
        regex = re.compile(filter_text, re.I)
        for row_idx in range(table.rowCount()):
            col_idx = 1
            package_name = table.item(row_idx, col_idx).text()
            table.setRowHidden(row_idx, not(bool(regex.search(package_name))))

    def create_packages_table(self):
        table = QTableWidget()
        column_labels = [
            "Pos",
            "Package name",
            "Status",
            "Progress",
            "Size",
        ]
        table.setColumnCount(len(column_labels))
        table.setHorizontalHeaderLabels(column_labels)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        # table.setSelectionMode(QTableWidget.SingleSelection)
        table.itemSelectionChanged.connect(self.on_package_selected)
        table.itemDoubleClicked.connect(self.on_package_doubleclicked)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeaderItem(0).setToolTip("Position")
        table.sortItems(0, Qt.AscendingOrder)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # TODO filter by search expression (regex?)
        # TODO select multiple packages -> rightclick -> remove / ...
        return table

    def create_bottom_view(self):
        self.bottom_view_stack = stack = QStackedWidget()
        for view_name in self.bottom_view_names:
            if view_name == "Package":
                self.package_package_view = view = self.create_package_package_view()
            elif view_name == "Links":
                self.package_links_table = view = self.create_package_links_view()
            elif view_name == "Downloads":
                self.package_downloads_view = view = self.create_package_downloads_view()
            elif view_name == "Files":
                self.package_files_view = view = self.create_package_files_view()
            stack.addWidget(view)
        stack.setCurrentIndex(self.default_bottom_view_idx)
        return stack

    def get_bottom_view_idx(self):
        return self.bottom_view_stack.currentIndex()

    def set_bottom_view_idx(self, bottom_view_idx):
        self.bottom_view_stack.setCurrentIndex(bottom_view_idx)
        self.refresh_bottom_view()

    def create_package_package_view(self):
        label = QLabel("")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        return label

    def create_package_links_view(self):
        # Package links table
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Pos",
            "Link", # link name
            "Plugin",
            "Status",
            "Error",
        ])
        table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.ExtendedSelection)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_package_links_context_menu)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeaderItem(0).setToolTip("Position")
        table.sortItems(0, Qt.AscendingOrder)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        return table

    def create_package_downloads_view(self):
        table = QTableWidget()
        column_labels = [
            "Pos",
            "Package", # package name
            "Link", # link name
            "Progress",
            "Size",
            "Plugin",
            "Status",
            "Info",
        ]
        table.setColumnCount(len(column_labels))
        table.setHorizontalHeaderLabels(column_labels)
        table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.ExtendedSelection)
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_package_links_context_menu)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeaderItem(0).setToolTip("Position")
        table.sortItems(0, Qt.AscendingOrder)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # TODO add context menu
        return table

    def refresh_package_downloads_view(self):
        self.client.links(self.on_package_downloads_data)

    def on_package_downloads_data(self, links):
        # TODO what is links["ids"]? these are different from link["fid"]
        # print("links", links)
        table = self.package_downloads_view
        table.setRowCount(len(links["links"]))
        for row, link in enumerate(links["links"]):
            col = 0

            # Position
            item = SortKeyTableWidgetItem(str(row + 1), (row + 1))
            item.setData(Qt.UserRole, link["fid"])  # Store file ID
            # TODO also store package_id?
            table.setItem(row, col, item)
            col += 1

            # Package name
            item = QTableWidgetItem(link["package_name"])
            table.setItem(row, col, item)
            col += 1

            # Link name
            item = QTableWidgetItem(link["name"])
            table.setItem(row, col, item)
            col += 1

            # Progress
            if link["size"] > 0:
                progress = ((link["size"] - link["bleft"]) / link["size"]) * 100
                progress_text = f"{progress:.1f}%"
            else:
                progress = 0
                progress_text = "0.0%"
            item = SortKeyTableWidgetItem(progress_text, progress)
            table.setItem(row, col, item)
            col += 1

            # Size
            size = link["size"]
            # FIXME pyload: zero size is "0.00 Bit"
            # size_text = link["format_size"]
            size_text = link["format_size"] if link["size"] > 0 else "0"
            item = SortKeyTableWidgetItem(size_text, size)
            table.setItem(row, col, item)
            col += 1

            # Plugin
            table.setItem(row, col, QTableWidgetItem(link["plugin"]))
            col += 1

            # Status
            # todo? map from link["status"] to custom order
            item = SortKeyTableWidgetItem(link["statusmsg"], link["status"])
            table.setItem(row, col, item)
            col += 1

            # Info
            table.setItem(row, col, QTableWidgetItem(link["info"]))
            col += 1

    def create_package_files_view(self):
        table = QTableWidget(parent=self)
        column_labels = [
            "File",
            "Size",
            "Modified",
        ]
        table.setColumnCount(len(column_labels))
        table.setHorizontalHeaderLabels(column_labels)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        # TODO increase width of the "Modified" column. make room for YYYY-mm-dd HH:mm:ss
        table.setColumnWidth(2, 135)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        # table.setSelectionMode(QTableWidget.SingleSelection)
        # table.itemSelectionChanged.connect(self.on_package_selected)
        table.itemDoubleClicked.connect(self.on_package_files_view_file_doubleclicked)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        table.sortItems(0, Qt.AscendingOrder)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # TODO filter by search expression (regex?)
        return table

    def on_package_files_view_file_doubleclicked(self):
        print("todo handle file doubleclicked")
        table = self.package_files_view

    def update_package_files_view(self):
        if not self.current_package:
            print("update_package_files_view: no self.current_package")
            return
        pid = self.selected_package_pid
        subdir = self.package_files_subdir
        self.client.get_package_folder_files(self.on_package_files_data, package_id=pid, subdir=subdir)

    def on_package_files_data(self, file_details_list):
        # print(f"file_details_list {json.dumps(file_details_list, indent=2)}")
        table = self.package_files_view
        if file_details_list is None or isinstance(file_details_list, QNetworkReply.NetworkError):
            # this can happen when the folder does not exist
            # QNetworkReply.NetworkError.InternalServerError
            table.setRowCount(0)
            return
        # table.setRowCount(0)
        # FIXME sometimes size and modified values are not rendered
        # but they are rendered later on table resize (repaint)
        _debug_package_files_view = False
        if _debug_package_files_view:
            print("on_package_files_data")
        table.setRowCount(len(file_details_list))
        # TODO add "../" special file in subdirs
        # if self.package_files_subdir != ""
        for row, file_details in enumerate(file_details_list):
            col = 0

            is_dir = (file_details["type"][0] == "d")

            # File name
            name = file_details["name"]
            if is_dir:
                name += "/"
            item = QTableWidgetItem(name)
            table.setItem(row, col, item)
            col += 1

            # Size
            if is_dir:
                size = 0
                size_text = ""
            else:
                size = file_details["size"]
                size_mb = size / (1024 * 1024)
                size_text = f"{size_mb:.2f} MB"
            # item = SortKeyTableWidgetItem(size_text, size)
            item = QTableWidgetItem(size_text)
            table.setItem(row, col, item)
            col += 1

            # Modified
            mtime = file_details["mtime"]
            mtime_text = datetime.datetime.fromtimestamp(mtime).strftime("%F %T")
            item = QTableWidgetItem(mtime_text)
            table.setItem(row, col, item)
            col += 1

            if _debug_package_files_view:
                print(" ", file_details["type"][0], mtime_text, (size_text or "0.00 MB"), name)

    def update_package_package_view(self):
        selected_items = self.packages_table.selectedItems()
        if not selected_items:
            self.package_package_view.setText("")
            return
        def on_package_data_received(package_data):
            self.current_package = package_data
            # if not self.current_package:
            #     self.package_package_view.setText("")
            #     return
            p = self.current_package
            text = "\n".join([
                f"package id: {p['pid']}",
                f"folder: {p['folder']}",
                f"password: {p['password']}",
                f"links: {len(p['links'])}",
            ])
            # self.package_package_view.setText(json.dumps(self.current_package, indent=2))
            self.package_package_view.setText(text)
        pid = self.packages_table.item(selected_items[0].row(), 0).data(Qt.UserRole)
        assert pid # TODO can this be None?
        self.client.get_package_data(on_package_data_received, pid)

    def create_bottom_view_button_group(self, main_layout):
        self.bottom_view_button_group = group = QButtonGroup(self)
        widget = QWidget()
        layout = QHBoxLayout(widget)
        self.bottom_view_button_list = []

        bottom_view_id_enum_args = []

        def add_button(idx, name):
            button = QPushButton(name, self)
            group.addButton(button)
            layout.addWidget(button)
            # button.clicked.connect(lambda b=button: self.toggle_bottom_view(b)) # b == True ?!
            # button.clicked.connect(lambda i=button_idx: self.toggle_bottom_view(i)) # i == True ?!
            button.clicked.connect(lambda: self.toggle_bottom_view(idx))
            button.setCheckable(True)
            self.bottom_view_button_list.append(button)
            bottom_view_id_enum_args.append((idx, name))
            return button

        button_idx = -1

        for name in self.bottom_view_names:
            button_idx += 1
            button = add_button(button_idx, name)
            if name == self.default_bottom_view_name:
                # this button is checked
                button.setChecked(True)
                self.bottom_button_checked_id = group.id(button)
                self.bottom_button_checked_button = button
                self.bottom_view_idx = button_idx

        assert self.bottom_view_idx

        self.BottomViewIdx = Object()
        for idx, name in bottom_view_id_enum_args:
            setattr(self.BottomViewIdx, name, idx)
        assert self.BottomViewIdx.Links

        main_layout.addWidget(widget)

    def toggle_bottom_view(self, clicked_button_idx):
        clicked_button = self.bottom_view_button_list[clicked_button_idx]
        if clicked_button_idx == self.bottom_view_idx:
            self.bottom_view_button_group.setExclusive(False)
            clicked_button.setChecked(False)
            self.bottom_view_idx = None
            self.bottom_view.hide()
        else:
            clicked_button.setChecked(True)
            self.bottom_view_button_group.setExclusive(True)
            self.bottom_view_idx = clicked_button_idx
            self.bottom_view.show()
            self.set_bottom_view_idx(clicked_button_idx)

    def start_downloads(self):
        cb = lambda *a: print("start_downloads: done")
        self.client.unpause_server(cb)

    def pause_downloads(self):
        cb = lambda *a: print("pause_downloads: done")
        self.client.pause_server(cb)

    def stop_downloads(self):
        cb = lambda *a: print("stop_downloads: done")
        self.client.stop_all_downloads(cb)

    # def on_stop_all_downloads(self):
    #     print("on_stop_all_downloads")

    def remove_finished(self):
        print("TODO remove_finished")

    def restart_failed(self):
        cb = lambda *a: print("restart_failed: done")
        self.client.restart_failed(cb)

    def move_package_to_top(self):
        print("TODO move_package_to_top")

    def remove_unfinished_links(self):
        table = self.packages_table
        pids = []
        for item in table.selectedItems():
            if item.column() != 0: continue
            pid = item.data(Qt.UserRole)
            pids.append(pid)
        if not pids:
            QMessageBox.information(self, "Error", "No packages selected")
            return
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove unfinished links in {len(pids)} packages?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        def on_delete_unfinished_links(res):
            # TODO handle errors
            print("delete_unfinished_links result", res)
            QMessageBox.information(self, "Success", f"Removed {res} links")
            self.refresh_queue()
        self.client.delete_unfinished_links(on_delete_unfinished_links, package_ids=pids)

    def show_package_links_context_menu(self, position):
        selected_rows = set(index.row() for index in self.package_links_table.selectedIndexes())
        if not selected_rows:
            return

        menu = QMenu()
        copy_action = menu.addAction("Copy Links")
        remove_action = menu.addAction("Remove Links")
        action = menu.exec(self.package_links_table.viewport().mapToGlobal(position))

        if action == copy_action:
            self.copy_selected_links()
        elif action == remove_action:
            self.remove_selected_links()

    def copy_selected_links(self):
        table = self.package_links_table
        links = []
        for item in table.selectedItems():
            if item.column() != 1: continue
            link = item.data(Qt.UserRole) # get file URL
            links.append(link)
        self.set_clipboard("".join(map(lambda s: s + "\n", links)))

    def set_clipboard(self, text):
        # https://stackoverflow.com/a/23119741/10440128
        cb = QApplication.clipboard()
        cb.clear(mode=QClipboard.Clipboard)
        cb.setText(text, mode=QClipboard.Clipboard)

    def remove_selected_links(self):
        # FIXME update package progress after removing files (links)
        table = self.package_links_table
        fids = []
        for item in table.selectedItems():
            if item.column() != 0: continue
            fid = item.data(Qt.UserRole)
            fids.append(fid)

        if not fids:
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Remove {len(fids)} links?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # self._debug_remove_links = True
        if self._debug_remove_links:
            print("links before remove")
            for i, link in enumerate(self.current_package["links"]):
                print(" ", i + 1, link["fid"], link["statusmsg"], link["url"])
            print("removing links")
            for i, link in enumerate(self.current_package["links"]):
                if link["fid"] in fids:
                    print(" ", i + 1, link["fid"], link["statusmsg"], link["url"])

        self.client.delete_files(self.on_files_deleted, file_ids=fids)

        # no. dont trust the server to remove links -> fetch new package data in on_files_deleted
        # also remove links from self.current_package
        # self.current_package["links"] = list(filter(lambda l: l["fid"] not in fids, self.current_package["links"]))

    def on_files_deleted(self, result):
        if result is None:
            # QMessageBox.information(self, "Success", "Links removed successfully")
            # Refresh the package data to show changes
            if self.current_package:
                pid = self.current_package["pid"]
                assert pid # TODO can this be None?
                self.client.get_package_data(self.on_package_data_received, pid)
        else:
            QMessageBox.warning(self, "Error", f"Failed to remove links: {result}")

    def show_add_package_dialog(self):
        dialog = AddPackageDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, links, password = dialog.get_package_data()
            if not name:
                QMessageBox.warning(self, "Error", "Package name cannot be empty")
                return
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

    def login(self):
        self.client.login(self.on_login_result, username="pyload", password="pyload")

    def on_login_result(self, success):
        if success:
            self.get_config()
            self.refresh_queue()
        else:
            QMessageBox.critical(self, "Login Failed", "Could not login to pyLoad")

    def get_config(self):
        self.client.get_config(self.on_config)

    def on_config(self, config):
        if isinstance(config, NetworkError):
            print("on_config error", config)
            return
        # print("on_config", json.dumps(config, indent=2))
        self.config = config

    def get_config_value(self, scope, key):
        scope_obj = self.config.get(scope)
        if scope_obj is None: raise KeyError(scope)
        for item in scope_obj["items"]:
            if item["name"] == key:
                return item["value"]
        # item was not found in scope
        raise KeyError(f"{scope}.{key}")

    def init_refresh_timer(self):
        self.refresh_timer = timer = QTimer()
        timer.timeout.connect(self.refresh_timer_tick)
        timer.start(self.refresh_interval * 1000)

    def refresh_timer_tick(self):
        self.refresh_bottom_view()

    def refresh_bottom_view(self):
        pid = self.selected_package_pid
        bottom_view_idx = self.get_bottom_view_idx()
        if bottom_view_idx == self.BottomViewIdx.Package:
            self.update_package_package_view()
        elif bottom_view_idx == self.BottomViewIdx.Links:
            if pid:
                self.client.get_package_data(self.on_package_data_received, pid)
        elif bottom_view_idx == self.BottomViewIdx.Downloads:
            self.refresh_package_downloads_view()
        elif bottom_view_idx == self.BottomViewIdx.Files:
            if pid:
                # TODO refactor
                def on_package_data_received(res):
                    self.current_package = res
                    self.update_package_files_view()
                self.client.get_package_data(on_package_data_received, pid)
            else:
                # no package selected
                self.update_package_files_view()

        # TODO refresh status
        """
        http://localhost:8000/json/status
        {
            "pause": false,
            "active": 2,
            "queue": 14194,
            "total": 14859,
            "speed": 55321.0,
            "download": true,
            "reconnect": false,
            "captcha": false,
            "proxy": false
        }
        """

    def refresh_queue(self):
        self.client.get_queue_and_collector(self.on_queue_and_collector_received)

    def on_queue_and_collector_received(self, queue_data):
        # FIXME preserve the previous sort order
        # https://stackoverflow.com/questions/11826257
        self.debug_pid = None
        if self.debug_pid:
            for pkg in queue_data:
                if pkg["pid"] == self.debug_pid:
                    print(f"on_queue_received pkg {self.debug_pid} = {json.dumps(pkg, indent=2)}")
                    break
        self.queue_data_cache = queue_data
        if queue_data is None:
            QMessageBox.warning(self, "Error", "Could not fetch queue")
            return

        self.packages_table.setRowCount(len(queue_data))
        for row, package in enumerate(queue_data):
            col = 0

            # Position
            position_item = SortKeyTableWidgetItem(str(row + 1), (row + 1))
            position_item.setData(Qt.UserRole, package["pid"])  # Store package ID
            self.packages_table.setItem(row, col, position_item)
            col += 1

            # Name
            name_item = QTableWidgetItem(package["name"])
            self.packages_table.setItem(row, col, name_item)
            col += 1

            # Status: Queue or Collector
            status_str = "Active" if package["queue"] else "Paused"
            item = QTableWidgetItem(status_str)
            item.setData(Qt.UserRole, package["queue"])
            self.packages_table.setItem(row, col, item)
            col += 1

            # Progress
            if package["sizetotal"] > 0:
                progress = (package["linksdone"] / package["linkstotal"])
                progress_text = f"{(progress * 100):.1f}%"
            else:
                progress = 0
                progress_text = "0.0%"
            # self.packages_table.setItem(row, 1, QTableWidgetItem(progress_text))
            progress_item = SortKeyTableWidgetItem(progress_text, progress)
            progress_item.setData(Qt.UserRole, progress)
            self.packages_table.setItem(row, col, progress_item)
            col += 1

            # Size
            size = package["sizetotal"]
            size_mb = package["sizetotal"] / (1024 * 1024)
            size_text = f"{size_mb:.2f} MB"
            # self.packages_table.setItem(row, 2, QTableWidgetItem(size_text))
            size_item = SortKeyTableWidgetItem(size_text, size)
            self.packages_table.setItem(row, col, size_item)
            col += 1

    def on_package_selected(self):
        selected_items = self.packages_table.selectedItems()
        if not selected_items:
            return

        # Get package ID from the first column of selected row
        pid = self.packages_table.item(selected_items[0].row(), 0).data(Qt.UserRole)
        assert pid # TODO can this be None?
        self.selected_package_pid = pid
        self.refresh_bottom_view()

    def on_package_doubleclicked(self):
        selected_items = self.packages_table.selectedItems()
        if not selected_items:
            return
        if not self.client.is_localhost: return

        storage_folder = self.get_config_value("general", "storage_folder")

        def on_package_data_received(package_data):
            # print(f"on_package_doubleclicked package_data {package_data}")
            folder_path = os.path.join(storage_folder, package_data["folder"])
            if not os.path.exists(folder_path):
                print(f"missing folder_path {folder_path!r}")
                return
            args = [
                "xdg-open",
                folder_path,
            ]
            subprocess.Popen(args)

        pid = self.packages_table.item(selected_items[0].row(), 0).data(Qt.UserRole)
        assert pid # TODO can this be None?
        self.client.get_package_data(on_package_data_received, pid)

    def on_package_data_received(self, package_data):
        if package_data is None:
            self.package_links_table.setRowCount(0)
            return
        if self._debug_package_data:
            for pkg in self.queue_data_cache:
                if pkg["pid"] == package_data["pid"]:
                    print(f"on_package_data_received: queue_data[] = {json.dumps(pkg, indent=2)}")
                    break
            print(f"on_package_data_received: package_data = {json.dumps(package_data, indent=2)}")
            if package_data is None:
                self.package_links_table.setRowCount(0)
                return

        self.current_package = package_data

        if self._debug_remove_links:
            print("links after remove")
            for i, link in enumerate(self.current_package["links"]):
                print(" ", i + 1, link["fid"], link["statusmsg"], link["url"])
            self._debug_remove_links = False

        # this seems to be necessary to fix table updates
        # without this, the result table can contain duplicate values
        # TODO why?
        self.package_links_table.setRowCount(0)

        links = package_data.get("links", [])
        self.package_links_table.setRowCount(len(links))

        # FIXME this can produce broken tables with duplicate position values

        for row, link in enumerate(links):
            col = 0

            # Position
            position_item = SortKeyTableWidgetItem(str(row + 1), (row + 1))
            position_item.setData(Qt.UserRole, link["fid"])  # Store file ID
            self.package_links_table.setItem(row, col, position_item)
            col += 1

            # Filename
            item = QTableWidgetItem(link["name"])
            item.setData(Qt.UserRole, link["url"])  # Store file URL
            self.package_links_table.setItem(row, col, item)
            col += 1

            # Plugin
            self.package_links_table.setItem(row, col, QTableWidgetItem(link["plugin"]))
            col += 1

            # Status
            # todo? map from link["status"] to custom order
            status_item = SortKeyTableWidgetItem(link["statusmsg"], link["status"])
            self.package_links_table.setItem(row, col, status_item)
            col += 1

            # Error
            # TODO add tooltip with full error message
            self.package_links_table.setItem(row, col, QTableWidgetItem(link["error"]))
            col += 1

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
            QMessageBox.information(self, "Success", "Package added successfully")
            self.refresh_queue()
        else:
            QMessageBox.warning(self, "Error", "Failed to add package")

if __name__ == "__main__":
    # handle Ctrl+C from terminal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    window = PyLoadUI()
    window.show()
    app.exec()
