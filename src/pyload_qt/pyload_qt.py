#!/usr/bin/env python3

import os
import sys
import signal
import json
import re
import subprocess
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
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtCore import QTimer
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtGui import QIcon, QScreen
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtGui import QFont


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
        self.config_path = None
        self.config = {}
        if self.is_localhost:
            # FIXME this is the default config path, it can be different
            self.config_path = "~/.pyload/settings/pyload.cfg"
            self.parse_config()

    def parse_config(self):
        with open(os.path.expanduser(self.config_path)) as f:
            group = None
            for line in f.readlines():
                line = line.rstrip()
                # print(f"line {line!r}")
                if line.startswith("version:"): continue
                elif line == "": continue
                elif line[0] == "\t":
                    m = re.fullmatch(r'\t([0-9a-zA-Z_;]+) ([0-9a-zA-Z_]+) : "[^"]+" = ?(.*)', line)
                    _type, key, val = m.groups()
                    if _type == "bool": val = True if val == "True" else False
                    elif _type == "int": val = int(val)
                    group[key] = val
                else:
                    m = re.fullmatch(r'([0-9a-zA-Z_]+) - "[^"]+":', line)
                    key = m.group(1)
                    group = self.config[key] = dict()

    # https://stackoverflow.com/questions/13194180/dynamic-method-generation-in-python
    def __getattr__(self, name):
        print(f"getattr {name}")
        try:
            return self.func_cache[name]
        except KeyError:
            pass
        print(f"creating function {name}")
        # def func(self, *args, **kwargs, callback): # ?
        # def func(self, *args, callback=None, **kwargs): # ?
        # def func(*args, callback=None, **kwargs): # ?
        # def func(self, callback, *args, **kwargs):
        def func(callback, *args, **kwargs):
            if name in ("status", "links"):
                api_dir = "json"
            else:
                api_dir = "api"
            url = f"{self.base_url}/{api_dir}/{name}"
            if args:
                url += "/" + ",".join(map(str, args))
            if kwargs:
                kwargs_json = dict()
                for key, val in kwargs.items():
                    kwargs_json[key] = json.dumps(val, separators=(",", ":"))
                url += "?" + urllib.parse.urlencode(kwargs_json)
            request = QNetworkRequest(QUrl(url))
            if self.session_cookie:
                request.setRawHeader(b"Cookie", self.session_cookie.encode())
            reply = self.manager.get(request)
            def handle_reply():
                if reply.error() == QNetworkReply.NoError:
                    data = json.loads(reply.readAll().data().decode())
                    if callback: callback(data)
                else:
                    # TODO also print response body with the server exception
                    print(f"{name} reply.error", reply.error())
                    if callback: callback(None)
                reply.deleteLater()
            reply.finished.connect(handle_reply)
        func.__name__ = name
        self.func_cache[name] = func
        return func

    def login(self, username, password, callback):
        url = f"{self.base_url}/api/login"
        request = QNetworkRequest(QUrl(url))
        request.setHeader(
            QNetworkRequest.ContentTypeHeader, "application/x-www-form-urlencoded"
        )

        post_data = f"username={username}&password={password}".encode()
        reply = self.manager.post(request, post_data)

        def handle_reply():
            if reply.error() == QNetworkReply.NoError:
                cookies = reply.header(QNetworkRequest.SetCookieHeader)
                if cookies:
                    self.session_cookie = cookies[0].toRawForm().data().decode()
                    callback(True)
                else:
                    callback(False)
            else:
                print("login: error", reply.error())
                callback(False)
            reply.deleteLater()

        reply.finished.connect(handle_reply)

    def get_queue(self, callback):
        url = f"{self.base_url}/api/get_queue"
        request = QNetworkRequest(QUrl(url))
        if self.session_cookie:
            request.setRawHeader(b"Cookie", self.session_cookie.encode())

        reply = self.manager.get(request)

        def handle_reply():
            if reply.error() == QNetworkReply.NoError:
                data = json.loads(reply.readAll().data().decode())
                callback(data)
            else:
                callback(None)
            reply.deleteLater()

        reply.finished.connect(handle_reply)

    def get_package_data(self, pid, callback):
        url = f"{self.base_url}/api/get_package_data/{pid}"
        request = QNetworkRequest(QUrl(url))
        if self.session_cookie:
            request.setRawHeader(b"Cookie", self.session_cookie.encode())

        reply = self.manager.get(request)

        def handle_reply():
            if reply.error() == QNetworkReply.NoError:
                data = json.loads(reply.readAll().data().decode())
                callback(data)
            else:
                callback(None)
            reply.deleteLater()

        reply.finished.connect(handle_reply)

    def add_package(self, name, links, callback):
        encoded_name = json.dumps(name)
        encoded_links = json.dumps(links)
        url = f"{self.base_url}/api/add_package?name={encoded_name}&links={encoded_links}"
        request = QNetworkRequest(QUrl(url))
        if self.session_cookie:
            request.setRawHeader(b"Cookie", self.session_cookie.encode())

        reply = self.manager.get(request)

        def handle_reply():
            if reply.error() == QNetworkReply.NoError:
                callback(True)
            else:
                callback(False)
            reply.deleteLater()

        reply.finished.connect(handle_reply)

    def delete_files(self, fids, callback):
        if not fids:
            callback(False)
            return
        encoded_fids = json.dumps(fids, separators=(",", ":"))
        url = f"{self.base_url}/api/delete_files?file_ids={encoded_fids}"
        request = QNetworkRequest(QUrl(url))
        if self.session_cookie:
            request.setRawHeader(b"Cookie", self.session_cookie.encode())

        reply = self.manager.get(request)

        def handle_reply():
            if reply.error() == QNetworkReply.NoError:
                callback(True)
            else:
                # TODO also print response body with the server exception
                print("delete_files reply.error", reply.error())
                callback(False)
            reply.deleteLater()

        reply.finished.connect(handle_reply)


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
        return name, links


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


class PyLoadUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client = PyLoadClient()
        self.current_package = None
        self.init_ui()
        self.login()
        self.refresh_interval = 5 # refresh every 5 seconds
        self.init_refresh_timer()

    def init_ui(self):
        self.setWindowTitle("pyLoad")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon(os.path.dirname(__file__) + "/pyload-logo.png"))

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
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

        self.default_bottom_view_name = "Links"
        self.default_bottom_view_idx = self.bottom_view_names.index(self.default_bottom_view_name)

        self.create_bottom_view_button_group(main_layout)
        self.bottom_view = self.create_bottom_view()

        splitter.addWidget(self.packages_table)
        splitter.addWidget(self.bottom_view)
        splitter.setSizes([300, 200])

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

        def add_text_button(label, tooltip, action, size=25, bold=False):
            # https://stackoverflow.com/a/79735780/10440128
            button = QToolButton()
            _action = QAction()
            _action.setToolTip(tooltip)
            _action.triggered.connect(action)
            button.setDefaultAction(_action)
            layout = QVBoxLayout(button)
            _label = QLabel(label)
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

    def create_packages_table(self):
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels([
            "Pos",
            "Package name",
            "Progress",
            "Size",
        ])
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
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
        return QLabel("TODO package view")

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
        return QLabel("TODO files view")

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

    def show_package_links_context_menu(self, position):
        selected_rows = set(index.row() for index in self.package_links_table.selectedIndexes())
        if not selected_rows:
            return

        menu = QMenu()
        remove_action = menu.addAction("Remove Links")
        action = menu.exec(self.package_links_table.viewport().mapToGlobal(position))

        if action == remove_action:
            self.remove_selected_links()

    def remove_selected_links(self):
        selected_rows = set(index.row() for index in self.package_links_table.selectedIndexes())
        if not selected_rows:
            return

        if not self.current_package or "links" not in self.current_package:
            return

        # Get the fids of selected links
        fids = []
        for row in selected_rows:
            if row < len(self.current_package["links"]):
                link = self.current_package["links"][row]
                fids.append(link["fid"])

        if not fids:
            return

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove {len(fids)} link(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.client.delete_files(fids, self.on_files_deleted)

    def on_files_deleted(self, success):
        if success:
            # QMessageBox.information(self, "Success", "Links removed successfully")
            # Refresh the package data to show changes
            if self.current_package:
                pid = self.current_package["pid"]
                self.client.get_package_data(pid, self.on_package_data_received)
        else:
            QMessageBox.warning(self, "Error", "Failed to remove links")

    def show_add_package_dialog(self):
        dialog = AddPackageDialog(self)
        if dialog.exec() == QDialog.Accepted:
            name, links = dialog.get_package_data()
            if not name:
                QMessageBox.warning(self, "Error", "Package name cannot be empty")
                return
            if not links:
                QMessageBox.warning(self, "Error", "No valid links found")
                return

            self.client.add_package(name, links, self.on_package_added)

    def login(self):
        self.client.login("pyload", "pyload", self.on_login_result)

    def on_login_result(self, success):
        if success:
            self.refresh_queue()
        else:
            QMessageBox.critical(self, "Login Failed", "Could not login to pyLoad")

    def init_refresh_timer(self):
        self.refresh_timer = timer = QTimer()
        timer.timeout.connect(self.refresh_timer_tick)
        timer.start(self.refresh_interval * 1000)

    def refresh_timer_tick(self):
        self.refresh_bottom_view()

    def refresh_bottom_view(self):
        bottom_view_idx = self.get_bottom_view_idx()
        if bottom_view_idx == self.BottomViewIdx.Package:
            pass
        elif bottom_view_idx == self.BottomViewIdx.Links:
            pass
        elif bottom_view_idx == self.BottomViewIdx.Downloads:
            self.refresh_package_downloads_view()
        elif bottom_view_idx == self.BottomViewIdx.Files:
            pass

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
        self.client.get_queue(self.on_queue_received)

    def on_queue_received(self, queue_data):
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

            # Progress
            if package["sizetotal"] > 0:
                progress = (package["linksdone"] / package["linkstotal"]) * 100
                progress_text = f"{progress:.1f}%"
            else:
                progress = 0
                progress_text = "0.0%"
            # self.packages_table.setItem(row, 1, QTableWidgetItem(progress_text))
            progress_item = SortKeyTableWidgetItem(progress_text, progress)
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
        self.client.get_package_data(pid, self.on_package_data_received)

    def on_package_doubleclicked(self):
        selected_items = self.packages_table.selectedItems()
        if not selected_items:
            return
        if not self.client.is_localhost: return

        storage_folder = self.client.config["general"]["storage_folder"]

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
        self.client.get_package_data(pid, on_package_data_received)


    def on_package_data_received(self, package_data):
        if package_data is None:
            self.package_links_table.setRowCount(0)
            return

        self.current_package = package_data
        links = package_data.get("links", [])
        self.package_links_table.setRowCount(len(links))

        for row, link in enumerate(links):
            col = 0

            # Position
            position_item = SortKeyTableWidgetItem(str(row + 1), (row + 1))
            position_item.setData(Qt.UserRole, link["fid"])  # Store file ID
            self.package_links_table.setItem(row, col, position_item)
            col += 1

            # Filename
            self.package_links_table.setItem(row, col, QTableWidgetItem(link["name"]))
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

        self.client.add_package(name, links, self.on_package_added)

    def on_package_added(self, success):
        if success:
            QMessageBox.information(self, "Success", "Package added successfully")
            self.package_name_input.clear()
            self.links_input.clear()
            self.refresh_queue()
        else:
            QMessageBox.warning(self, "Error", "Failed to add package")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    app = QApplication(sys.argv)
    window = PyLoadUI()
    window.show()
    app.exec()
