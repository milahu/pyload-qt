from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QAbstractItemView,
)

from .sort_key_table_widget_item import SortKeyTableWidgetItem


class DownloadsMixin:

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
        # table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        # default column width is 100
        # NOTE leave room for vertical scrollbar
        table.setColumnWidth(0, 10) # Pos "12345"
        table.setColumnWidth(1, 280) # Package
        table.setColumnWidth(2, 150) # Link
        table.setColumnWidth(3, 70) # Progress "12.3%"
        table.setColumnWidth(4, 90) # Size "1000.00 MiB"
        # table.setColumnWidth(5, 100) # Plugin "RapidgatorNet"
        # table.setColumnWidth(6, 100) # Status "downloading"
        table.setColumnWidth(7, 160) # Info "00:01:23 @ 12.34 MiB/s"
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
        table.clearContents()
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
            item.setToolTip(link["package_name"])
            table.setItem(row, col, item)
            col += 1

            # Link name
            item = QTableWidgetItem(link["name"])
            item.setToolTip(link["name"])
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
            item = QTableWidgetItem(link["plugin"])
            item.setToolTip(link["plugin"])
            table.setItem(row, col, item)
            col += 1

            # Status
            # todo? map from link["status"] to custom order
            item = SortKeyTableWidgetItem(link["statusmsg"], link["status"])
            item.setToolTip(link["statusmsg"])
            table.setItem(row, col, item)
            col += 1

            # Info
            item = QTableWidgetItem(link["info"])
            item.setToolTip(link["info"])
            table.setItem(row, col, item)
            col += 1
