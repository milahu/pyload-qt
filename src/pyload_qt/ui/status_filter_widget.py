# based on
# https://github.com/qbittorrent/qBittorrent/blob/master/src/gui/transferlistfilters/statusfilterwidget.cpp

from PySide6.QtWidgets import (
    QListWidgetItem,
    QMenu,
    QListWidget,
)
from PySide6.QtCore import (
    Qt,
    Signal,
    QSize,
)
from PySide6.QtGui import QCursor

class StatusFilterWidget(QListWidget):
    # Signals
    filterChanged = Signal(str)

    _filter_names = [
        "All",
        "Active",
        "Paused",
        "Complete",
        "Incomplete",
        "Partial",
        "Empty",
    ]

    def __init__(self, parent=None, transfer_list=None):
        super().__init__(parent)
        self.transfer_list = transfer_list

        # Initialize counters
        self.m_nbActive = 0
        self.m_nbPaused = 0

        self.m_torrentsStatus = {}  # Dictionary instead of QHash

        # Add status filters
        self._setup_filter_items()

        # Connect signals
        self.currentRowChanged.connect(self.applyFilter)

    def _setup_filter_items(self):
        """Create all the filter items with their icons and text"""
        for filter_name in self._filter_names:
            item = QListWidgetItem(self)
            # item.setData(Qt.DisplayRole, self.tr(f"{filter_name} (0)"))
            item.setData(Qt.DisplayRole, self.tr(filter_name))

    def sizeHint(self):
        num_visible_items = 0
        for i in range(self.count()):
            if not self.item(i).isHidden():
                num_visible_items += 1

        return QSize(
            self.sizeHintForColumn(0),  # Width
            int((self.sizeHintForRow(0) + 2 * self.spacing()) * (num_visible_items + 0.5))  # Height
        )

    def updateTorrentStatus(self, torrent):
        if torrent not in self.m_torrentsStatus:
            self.m_torrentsStatus[torrent] = set()  # Using set instead of bitset

        torrent_status = self.m_torrentsStatus[torrent]

        def update_status(status, counter_attr):
            counter = getattr(self, counter_attr)
            has_status = status in torrent_status
            # need_status = TorrentFilter(status).match(torrent)  # This would use your TorrentFilter class

            # For demonstration, assuming need_status is determined somehow
            need_status = False  # Replace with actual logic

            if need_status and not has_status:
                setattr(self, counter_attr, counter + 1)
                torrent_status.add(status)
            elif not need_status and has_status:
                setattr(self, counter_attr, counter - 1)
                torrent_status.discard(status)

        # Update all status types
        update_status("Downloading", "m_nbDownloading")
        update_status("Seeding", "m_nbSeeding")
        update_status("Completed", "m_nbCompleted")
        update_status("Running", "m_nbRunning")
        update_status("Stopped", "m_nbStopped")
        update_status("Active", "m_nbActive")
        update_status("Inactive", "m_nbInactive")
        update_status("StalledUploading", "m_nbStalledUploading")
        update_status("StalledDownloading", "m_nbStalledDownloading")
        update_status("Checking", "m_nbChecking")
        update_status("Moving", "m_nbMoving")
        update_status("Errored", "m_nbErrored")

        self.m_nbStalled = self.m_nbStalledUploading + self.m_nbStalledDownloading

    def updateTexts(self):
        # session = Session.instance()
        # torrents_count = session.torrentsCount()
        torrents_count = 0  # Replace with actual count

        self.item(0).setData(Qt.DisplayRole, self.tr("All ({})").format(torrents_count))
        self.item(1).setData(Qt.DisplayRole, self.tr("Active ({})").format(self.m_nbActive))
        self.item(2).setData(Qt.DisplayRole, self.tr("Paused ({})").format(self.m_nbActive))

    def hideZeroItems(self):
        self.item(1).setHidden(self.m_nbActive == 0)
        self.item(2).setHidden(self.m_nbPaused == 0)

        if self.currentItem() and self.currentItem().isHidden():
            self.setCurrentRow(0)  # All

    def update(self, torrents):
        for torrent in torrents:
            self.updateTorrentStatus(torrent)

        self.updateTexts()

        # if Preferences.instance().getHideZeroStatusFilters():
        #     self.hideZeroItems()
        #     self.updateGeometry()

    def showMenu(self):
        menu = QMenu(self)
        menu.setAttribute(Qt.WA_DeleteOnClose)

        menu.popup(QCursor.pos())

    def applyFilter(self, row):
        if self.transfer_list:
            # self.transfer_list.applyStatusFilter(row)
            pass
        row_text = self.item(row).text()
        # remove the counter suffix
        # a: "Active (123)"
        # b: "Active"
        row_text = row_text.split(" (")[0]
        self.filterChanged.emit(row_text)

    def configure(self):
        for i in range(self.count()):
            self.item(i).setHidden(False)

        self.updateGeometry()

    def __del__(self):
        # Save current selection
        # Preferences.instance().setTransSelFilter(self.currentRow())
        pass
