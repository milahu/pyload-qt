import os
import re
import json
import time

from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
)

from .sort_key_table_widget_item import SortKeyTableWidgetItem


class PackagesMixin:

    def create_packages_table(self):
        table = QTableWidget()
        column_labels = []

        num_cols = 5

        # the package ID is useful for debugging
        self.packages_table_has_package_id_column = False
        # self.packages_table_has_package_id_column = True

        if self.packages_table_has_package_id_column:
            num_cols += 1

        # workaround: table.setColumnWidth works only if we call table.setColumnCount before
        table.setColumnCount(num_cols)

        col = 0

        # Position
        column_labels.append("Pos")
        # default column width is 100
        # NOTE leave room for vertical scrollbar
        table.setColumnWidth(col, 10) # Pos "12345"
        package_position_col = col
        col += 1

        if self.packages_table_has_package_id_column:
            # Package ID = "PID"
            column_labels.append("ID")
            table.setColumnWidth(col, 20)
            col += 1

        # Package Name
        column_labels.append("Package")
        table.setColumnWidth(col, 640)
        col += 1

        # Status: "Active" | "Paused"
        column_labels.append("Status")
        table.setColumnWidth(col, 150)
        col += 1

        # Progress "12.3%"
        column_labels.append("Progress")
        table.setColumnWidth(col, 70)
        col += 1

        # Size "1000.00 MiB"
        column_labels.append("Size")
        table.setColumnWidth(col, 90)
        col += 1

        # table.setColumnCount(len(column_labels))
        assert len(column_labels) == num_cols
        table.setHorizontalHeaderLabels(column_labels)
        # table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        # table.setSelectionMode(QTableWidget.SingleSelection)
        table.itemSelectionChanged.connect(self.on_package_selected)
        table.itemDoubleClicked.connect(self.on_package_doubleclicked)
        table.setSortingEnabled(True)
        table.verticalHeader().setVisible(False)
        # "Pos" is short for "Position"
        table.horizontalHeaderItem(package_position_col).setToolTip("Position")
        # sort by package position
        table.sortItems(package_position_col, Qt.AscendingOrder)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # TODO filter by search expression (regex?)
        # TODO select multiple packages -> rightclick -> remove / ...
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_packages_context_menu)
        return table

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
                    package_queue_item = table.item(row_idx, package_queue_col_idx)
                    if package_queue_item is None:
                        continue
                    package_queue = package_queue_item.data(Qt.UserRole)
                    if status_id == 1: # active aka "pyload queue"
                        hidden = not(package_queue)
                    elif status_id == 2: # paused aka "pyload collector"
                        hidden = package_queue
                if status_id in (3, 4, 5):
                    package_progress_item = table.item(row_idx, package_progress_col_idx)
                    if package_progress_item is None:
                        continue
                    package_progress = package_progress_item.data(Qt.UserRole)
                    if status_id == 3: # complete
                        hidden = (package_progress < 1)
                    elif status_id == 4: # partial
                        hidden = (package_progress in (0, 1))
                    elif status_id == 5: # empty
                        hidden = (package_progress > 0)
                table.setRowHidden(row_idx, hidden)

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

    def reload_packages_table(self):
        return self.refresh_queue()

    def refresh_queue(self):
        if 1:
            # debug timings
            self.t1_refresh_queue = time.time()
        self.client.get_queue_and_collector(self.on_queue_and_collector_received)

    def on_queue_and_collector_received(self, queue_data):
        # FIXME preserve the previous sort order
        # https://stackoverflow.com/questions/11826257
        if hasattr(self, "t1_refresh_queue"):
            # debug timings
            t1 = self.t1_refresh_queue
            t2 = time.time()
            print(f"on_queue_and_collector_received: received data: dt={t2 - t1:.2f} N={len(queue_data)}")
            t1 = time.time()
        if 0:
            # debug: limit queue size to get faster UI
            queue_data = queue_data[:100]
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

        table = self.packages_table
        table.clearContents()

        # disable table sorting to insert data 10x faster
        table.setSortingEnabled(False)
        table.setUpdatesEnabled(False)

        # FIXME move this to a "try" block
        self.packages_table.setRowCount(len(queue_data))
        for row, package in enumerate(queue_data):
            col = 0

            # Position
            position_item = SortKeyTableWidgetItem(str(row + 1), (row + 1))
            # package_id is stored in cell 0
            position_item.setData(Qt.UserRole, package["pid"])  # Store package ID
            self.packages_table.setItem(row, col, position_item)
            col += 1

            if self.packages_table_has_package_id_column:
                # Package ID = "PID"
                package_id = package["pid"] # package ID
                package_id_text = str(package_id)
                package_id_item = SortKeyTableWidgetItem(package_id_text, package_id)
                self.packages_table.setItem(row, col, package_id_item)
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

        # FIXME move this to a "finally" block
        # re-enable table sorting after all data was inserted
        table.setSortingEnabled(True)
        table.setUpdatesEnabled(True)

        if hasattr(self, "t1_refresh_queue"):
            # debug timings
            t2 = time.time()
            print(f"on_queue_and_collector_received: filled table: dt={t2 - t1:.2f} N={len(queue_data)}")

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

        storage_folder = self.get_config_value("core", "general", "storage_folder")

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
