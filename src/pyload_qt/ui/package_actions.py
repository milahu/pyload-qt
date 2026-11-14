from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QMessageBox,
    QMenu,
)


class PackageActionsMixin:

    def get_selected_package_ids(self):
        package_ids = []
        table = self.packages_table
        for item in table.selectedItems():
            # package_id is stored in cell 0
            if item.column() != 0: continue
            package_id = item.data(Qt.UserRole)
            package_ids.append(package_id)
        return package_ids

    def start_selected_packages(self):
        package_ids = self.get_selected_package_ids()
        if not package_ids:
            return
        # Moves package from Collector to Queue.
        self.client.push_to_queue(self.on_packages_started, package_ids=package_ids)

    def on_packages_started(self, response):
        print(f"on_packages_started: {response}")
        self.reload_packages_table()

    def pause_selected_packages(self):
        package_ids = self.get_selected_package_ids()
        if not package_ids:
            return
        # Moves package from Queue to Collector.
        self.client.pull_from_queue(self.on_packages_paused, package_ids=package_ids)

    def on_packages_paused(self, response):
        print(f"on_packages_paused: {response}")
        self.reload_packages_table()

    def remove_selected_packages(self):
        package_ids = self.get_selected_package_ids()
        if not package_ids:
            return
        self.client.delete_packages(self.on_packages_removed, package_ids=package_ids)

    def on_packages_removed(self, response):
        print(f"on_packages_removed: {response}")
        self.reload_packages_table()

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

    def move_packages_to_top(self):
        table = self.packages_table
        pids = []
        for item in table.selectedItems():
            if item.column() != 0: continue
            pid = item.data(Qt.UserRole)
            pids.append(pid)
        if not pids:
            QMessageBox.information(self, "Error", "No packages selected")
            return
        def on_move_packages_to_top(response):
            if response is None:
                self.reload_packages_table()
            else:
                # error
                # FIXME on_move_packages_to_top: NetworkError.InternalServerError
                # but when i close and restart the app, the packages were moved to the top
                print(f"on_move_packages_to_top: {response}")
        self.client.order_packages(on_move_packages_to_top, package_ids=pids, position=0)

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

    def show_packages_context_menu(self, position):
        selected_rows = set(index.row() for index in self.packages_table.selectedIndexes())
        if not selected_rows:
            return

        menu = QMenu()

        start_action = menu.addAction("Start Packages") # collector -> queue
        pause_action = menu.addAction("Pause Packages") # queue -> collector
        remove_action = menu.addAction("Remove Packages")
        # move_top_action = menu.addAction("Move Packages to Top")
        # move_bottom_action = menu.addAction("Move Packages to Bottom")
        # TODO more

        action = menu.exec(self.packages_table.viewport().mapToGlobal(position))

        if action == start_action:
            self.start_selected_packages()
        if action == pause_action:
            self.pause_selected_packages()
        elif action == remove_action:
            self.remove_selected_packages()
        # TODO more
