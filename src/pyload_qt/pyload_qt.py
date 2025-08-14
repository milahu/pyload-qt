#!/usr/bin/env python3

import os
import sys
import signal
import json
import re
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
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtGui import QIcon, QScreen
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtGui import QFont


class PyLoadClient:
    def __init__(self):
        self.manager = QNetworkAccessManager()
        # FIXME by default, the pyload server runs with ipv6
        # but with webui.develop=True in ~/.pyload/settings/pyload.cfg it runs with ipv4
        self.base_url = "http://localhost:8000/api" # ipv4: login fails with NetworkError.ConnectionRefusedError
        self.base_url = "http://127.0.0.1:8000/api" # ipv4: login fails with NetworkError.ConnectionRefusedError
        self.base_url = "http://[::1]:8000/api" # ipv6
        self.session_cookie = None
        self.func_cache = {}

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
            url = f"{self.base_url}/{name}"
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
        url = f"{self.base_url}/login"
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
        url = f"{self.base_url}/getQueue"
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
        url = f"{self.base_url}/getPackageData/{pid}"
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
        url = f"{self.base_url}/addPackage?name={encoded_name}&links={encoded_links}"
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
        url = f"{self.base_url}/delete_files?file_ids={encoded_fids}"
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


class PyLoadUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.client = PyLoadClient()
        self.current_package = None
        self.init_ui()
        self.login()

    def init_ui(self):
        self.setWindowTitle("PyLoad Client")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon(os.path.dirname(__file__) + "/pyload-logo.png"))

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        self.create_menu()

        self.create_toolbar()

        # Queue table
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(3)
        self.queue_table.setHorizontalHeaderLabels(["Pos", "Package name", "Progress", "Size"])
        self.queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.queue_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.queue_table.setSelectionMode(QTableWidget.SingleSelection)
        self.queue_table.itemSelectionChanged.connect(self.on_package_selected)
        self.queue_table.setSortingEnabled(True)
        self.queue_table.verticalHeader().setVisible(False)
        self.queue_table.horizontalHeaderItem(0).setToolTip("Position")
        self.queue_table.sortItems(0, Qt.AscendingOrder)

        # Package contents table
        self.contents_table = QTableWidget()
        self.contents_table.setColumnCount(5)
        self.contents_table.setHorizontalHeaderLabels([
            "Pos",
            "File name",
            "Plugin",
            "Status",
            "Error",
        ])
        self.contents_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.contents_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.contents_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.contents_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.contents_table.customContextMenuRequested.connect(self.show_contents_context_menu)
        self.contents_table.setSortingEnabled(True)
        self.contents_table.verticalHeader().setVisible(False)
        self.contents_table.horizontalHeaderItem(0).setToolTip("Position")
        self.contents_table.sortItems(0, Qt.AscendingOrder)

        # Splitter for tables
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.queue_table)
        splitter.addWidget(self.contents_table)
        splitter.setSizes([300, 200])

        # Add widgets to main layout
        main_layout.addWidget(splitter)

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

    def show_contents_context_menu(self, position):
        selected_rows = set(index.row() for index in self.contents_table.selectedIndexes())
        if not selected_rows:
            return

        menu = QMenu()
        remove_action = menu.addAction("Remove Links")
        action = menu.exec(self.contents_table.viewport().mapToGlobal(position))

        if action == remove_action:
            self.remove_selected_links()

    def remove_selected_links(self):
        selected_rows = set(index.row() for index in self.contents_table.selectedIndexes())
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

    def refresh_queue(self):
        self.client.get_queue(self.on_queue_received)

    def on_queue_received(self, queue_data):
        if queue_data is None:
            QMessageBox.warning(self, "Error", "Could not fetch queue")
            return

        self.queue_table.setRowCount(len(queue_data))
        for row, package in enumerate(queue_data):
            col = 0

            # Position
            position_item = SortKeyTableWidgetItem(str(row + 1), (row + 1))
            position_item.setData(Qt.UserRole, package["pid"])  # Store package ID
            self.queue_table.setItem(row, col, position_item)
            col += 1

            # Name
            name_item = QTableWidgetItem(package["name"])
            self.queue_table.setItem(row, col, name_item)
            col += 1

            # Progress
            if package["sizetotal"] > 0:
                progress = (package["sizedone"] / package["sizetotal"]) * 100
                progress_text = f"{progress:.1f}%"
            else:
                progress = 0
                progress_text = "0.0%"
            # self.queue_table.setItem(row, 1, QTableWidgetItem(progress_text))
            progress_item = SortKeyTableWidgetItem(progress_text, progress)
            self.queue_table.setItem(row, col, progress_item)
            col += 1

            # Size
            size = package["sizetotal"]
            size_mb = package["sizetotal"] / (1024 * 1024)
            size_text = f"{size_mb:.2f} MB"
            # self.queue_table.setItem(row, 2, QTableWidgetItem(size_text))
            size_item = SortKeyTableWidgetItem(size_text, size)
            self.queue_table.setItem(row, col, size_item)
            col += 1

    def on_package_selected(self):
        selected_items = self.queue_table.selectedItems()
        if not selected_items:
            return

        # Get package ID from the first column of selected row
        pid = self.queue_table.item(selected_items[0].row(), 0).data(Qt.UserRole)
        self.client.get_package_data(pid, self.on_package_data_received)

    def on_package_data_received(self, package_data):
        if package_data is None:
            self.contents_table.setRowCount(0)
            return

        self.current_package = package_data
        links = package_data.get("links", [])
        self.contents_table.setRowCount(len(links))

        for row, link in enumerate(links):
            col = 0

            # Position
            position_item = SortKeyTableWidgetItem(str(row + 1), (row + 1))
            position_item.setData(Qt.UserRole, link["fid"])  # Store file ID
            self.contents_table.setItem(row, col, position_item)
            col += 1

            # Filename
            self.contents_table.setItem(row, col, QTableWidgetItem(link["name"]))
            col += 1

            # Plugin
            self.contents_table.setItem(row, col, QTableWidgetItem(link["plugin"]))
            col += 1

            # Status
            self.contents_table.setItem(row, col, QTableWidgetItem(link["statusmsg"]))
            col += 1

            # Error
            self.contents_table.setItem(row, col, QTableWidgetItem(link["error"]))
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
