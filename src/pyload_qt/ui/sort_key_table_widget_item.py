from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
)


# https://stackoverflow.com/a/2304495/10440128
class SortKeyTableWidgetItem(QTableWidgetItem):
    def __init__(self, text, sortKey):
        #call custom constructor with UserType item type
        super().__init__(text, QTableWidgetItem.UserType)
        self.sortKey = sortKey

    #Qt uses a simple < check for sorting items, override this to use the sortKey
    def __lt__(self, other):
        return self.sortKey < other.sortKey
