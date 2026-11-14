from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
)

from .sort_key_table_widget_item import SortKeyTableWidgetItem


class LinksMixin:

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

    def on_package_data_received(self, package_data):
        # TODO? move to ui.packages
        table = self.package_links_table
        if package_data is None:
            table.clearContents()
            self.package_links_table.setRowCount(0)
            return
        if self._debug_package_data:
            for pkg in self.queue_data_cache:
                if pkg["pid"] == package_data["pid"]:
                    print(f"on_package_data_received: queue_data[] = {json.dumps(pkg, indent=2)}")
                    break
            print(f"on_package_data_received: package_data = {json.dumps(package_data, indent=2)}")
            if package_data is None:
                table.clearContents()
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
        table.clearContents()
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
            item = QTableWidgetItem(link["error"])
            item.setToolTip(link["error"])
            self.package_links_table.setItem(row, col, item)
            col += 1

    def show_package_links_context_menu(self, position):
        selected_rows = set(index.row() for index in self.package_links_table.selectedIndexes())
        if not selected_rows:
            return

        menu = QMenu()
        copy_action = menu.addAction("Copy Links")
        remove_action = menu.addAction("Remove Links")
        restart_action = menu.addAction("Restart Failed Links")
        action = menu.exec(self.package_links_table.viewport().mapToGlobal(position))

        if action == copy_action:
            self.copy_selected_links()
        elif action == remove_action:
            self.remove_selected_links()
        elif action == restart_action:
            self.restart_selected_links()

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

    def get_selected_package_link_ids(self):
        # note: pyload calls this "file_ids"
        table = self.package_links_table
        link_ids = []
        for item in table.selectedItems():
            # link_id is stored in cell 0
            if item.column() != 0: continue
            link_id = item.data(Qt.UserRole)
            link_ids.append(link_id)
        return link_ids

    def remove_selected_links(self):
        # FIXME update package progress after removing files (links)
        fids = self.get_selected_package_link_ids()
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

    def restart_selected_links(self):
        link_ids = self.get_selected_package_link_ids()
        if not link_ids:
            return
        # note: only restart *failed* links
        # -> dont lose finished links
        self.client.restart_failed(self.on_links_restarted, link_ids=link_ids)

    def on_links_restarted(self, response):
        print(f"on_links_restarted: {response}")
