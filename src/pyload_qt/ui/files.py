from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QTableWidget,
    QHeaderView,
    QAbstractItemView,
)
from PySide6.QtNetwork import (
    QNetworkReply,
)


class FilesMixin:

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
        # FIXME get_package_folder_files reply.error: NetworkError.ContentNotFoundError: {"error": "Not Found"}
        # does that mean "package files not found"?
        self.client.get_package_folder_files(self.on_package_files_data, package_id=pid, subdir=subdir)

    def on_package_files_data(self, file_details_list):
        # print(f"file_details_list {json.dumps(file_details_list, indent=2)}")
        table = self.package_files_view
        if file_details_list is None or isinstance(file_details_list, QNetworkReply.NetworkError):
            # this can happen when the folder does not exist
            # QNetworkReply.NetworkError.InternalServerError
            table.clearContents()
            table.setRowCount(0)
            return
        # table.setRowCount(0)
        # FIXME sometimes size and modified values are not rendered
        # but they are rendered later on table resize (repaint)
        _debug_package_files_view = False
        if _debug_package_files_view:
            print("on_package_files_data")
        table.clearContents()
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
