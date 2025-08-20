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
    filterChanged = Signal(int)

    def __init__(self, parent=None, transfer_list=None):
        super().__init__(parent)
        self.transfer_list = transfer_list

        # Initialize counters
        """
        self.m_nbDownloading = 0
        self.m_nbSeeding = 0
        self.m_nbCompleted = 0
        self.m_nbRunning = 0
        self.m_nbStopped = 0
        self.m_nbActive = 0
        self.m_nbInactive = 0
        self.m_nbStalled = 0
        self.m_nbStalledUploading = 0
        self.m_nbStalledDownloading = 0
        self.m_nbChecking = 0
        self.m_nbMoving = 0
        self.m_nbErrored = 0
        """
        self.m_nbActive = 0
        self.m_nbPaused = 0

        self.m_torrentsStatus = {}  # Dictionary instead of QHash

        # Add status filters
        self._setup_filter_items()

        # Connect signals
        self.currentRowChanged.connect(self.applyFilter)

        # These would be connected to actual session signals
        # session = Session.instance()
        # session.torrentsUpdated.connect(self.update)
        # session.torrentAboutToBeDeleted.connect(self.torrentAboutToBeDeleted)
        # session.torrentsLoaded.connect(self.handleTorrentsLoaded)

        # pref = Preferences.instance()
        # pref.changed.connect(self.configure)

        # Initial setup
        # torrents = session.torrents()
        # self.update(torrents)

        # stored_row = pref.getTransSelFilter()
        # if 0 <= stored_row < self.count() and not self.item(stored_row).isHidden():
        #     self.setCurrentRow(stored_row)
        # else:
        #     self.setCurrentRow(0)  # All

        # self.toggleFilter(pref.getStatusFilterState())

    def _setup_filter_items(self):
        """Create all the filter items with their icons and text"""
        # All
        all_item = QListWidgetItem(self)
        # all_item.setData(Qt.DisplayRole, self.tr("All (0)", "this is for the status filter"))
        all_item.setData(Qt.DisplayRole, self.tr("All", "this is for the status filter"))
        # all_item.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("filter-all", "filterall"))

        r"""
        # Downloading
        downloading = QListWidgetItem(self)
        downloading.setData(Qt.DisplayRole, self.tr("Downloading (0)"))
        # downloading.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("downloading"))

        # Seeding
        seeding = QListWidgetItem(self)
        seeding.setData(Qt.DisplayRole, self.tr("Seeding (0)"))
        # seeding.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("upload", "uploading"))

        # Completed
        completed = QListWidgetItem(self)
        completed.setData(Qt.DisplayRole, self.tr("Completed (0)"))
        # completed.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("checked-completed", "completed"))

        # Running
        running = QListWidgetItem(self)
        running.setData(Qt.DisplayRole, self.tr("Running (0)"))
        # running.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("torrent-start", "media-playback-start"))

        # Stopped
        stopped = QListWidgetItem(self)
        stopped.setData(Qt.DisplayRole, self.tr("Stopped (0)"))
        # stopped.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("stopped", "media-playback-pause"))
        """

        # Active
        active = QListWidgetItem(self)
        # active.setData(Qt.DisplayRole, self.tr("Active (0)"))
        active.setData(Qt.DisplayRole, self.tr("Active"))
        # active.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("filter-active", "filteractive"))

        # Paused
        paused = QListWidgetItem(self)
        # paused.setData(Qt.DisplayRole, self.tr("Paused (0)"))
        paused.setData(Qt.DisplayRole, self.tr("Paused"))
        # paused.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("paused", "media-playback-pause"))

        r"""
        # Inactive
        inactive = QListWidgetItem(self)
        inactive.setData(Qt.DisplayRole, self.tr("Inactive (0)"))
        # inactive.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("filter-inactive", "filterinactive"))

        # Stalled
        stalled = QListWidgetItem(self)
        stalled.setData(Qt.DisplayRole, self.tr("Stalled (0)"))
        # stalled.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("filter-stalled", "filterstalled"))

        # Stalled Uploading
        stalled_uploading = QListWidgetItem(self)
        stalled_uploading.setData(Qt.DisplayRole, self.tr("Stalled Uploading (0)"))
        # stalled_uploading.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("stalledUP"))

        # Stalled Downloading
        stalled_downloading = QListWidgetItem(self)
        stalled_downloading.setData(Qt.DisplayRole, self.tr("Stalled Downloading (0)"))
        # stalled_downloading.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("stalledDL"))

        # Checking
        checking = QListWidgetItem(self)
        checking.setData(Qt.DisplayRole, self.tr("Checking (0)"))
        # checking.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("force-recheck", "checking"))

        # Moving
        moving = QListWidgetItem(self)
        moving.setData(Qt.DisplayRole, self.tr("Moving (0)"))
        # moving.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("set-location"))

        # Errored
        errored = QListWidgetItem(self)
        errored.setData(Qt.DisplayRole, self.tr("Errored (0)"))
        # errored.setData(Qt.DecorationRole, UIThemeManager.instance().getIcon("error"))
        """

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

        r"""
        self.item(0).setData(Qt.DisplayRole, self.tr("All ({})").format(torrents_count))
        self.item(1).setData(Qt.DisplayRole, self.tr("Downloading ({})").format(self.m_nbDownloading))
        self.item(2).setData(Qt.DisplayRole, self.tr("Seeding ({})").format(self.m_nbSeeding))
        self.item(3).setData(Qt.DisplayRole, self.tr("Completed ({})").format(self.m_nbCompleted))
        self.item(4).setData(Qt.DisplayRole, self.tr("Running ({})").format(self.m_nbRunning))
        self.item(5).setData(Qt.DisplayRole, self.tr("Stopped ({})").format(self.m_nbStopped))
        self.item(6).setData(Qt.DisplayRole, self.tr("Active ({})").format(self.m_nbActive))
        self.item(7).setData(Qt.DisplayRole, self.tr("Inactive ({})").format(self.m_nbInactive))
        self.item(8).setData(Qt.DisplayRole, self.tr("Stalled ({})").format(self.m_nbStalled))
        self.item(9).setData(Qt.DisplayRole, self.tr("Stalled Uploading ({})").format(self.m_nbStalledUploading))
        self.item(10).setData(Qt.DisplayRole, self.tr("Stalled Downloading ({})").format(self.m_nbStalledDownloading))
        self.item(11).setData(Qt.DisplayRole, self.tr("Checking ({})").format(self.m_nbChecking))
        self.item(12).setData(Qt.DisplayRole, self.tr("Moving ({})").format(self.m_nbMoving))
        self.item(13).setData(Qt.DisplayRole, self.tr("Errored ({})").format(self.m_nbErrored))
        """
        self.item(0).setData(Qt.DisplayRole, self.tr("All ({})").format(torrents_count))
        self.item(1).setData(Qt.DisplayRole, self.tr("Active ({})").format(self.m_nbActive))
        self.item(2).setData(Qt.DisplayRole, self.tr("Paused ({})").format(self.m_nbActive))

    def hideZeroItems(self):
        r"""
        self.item(1).setHidden(self.m_nbDownloading == 0)
        self.item(2).setHidden(self.m_nbSeeding == 0)
        self.item(3).setHidden(self.m_nbCompleted == 0)
        self.item(4).setHidden(self.m_nbRunning == 0)
        self.item(5).setHidden(self.m_nbStopped == 0)
        self.item(6).setHidden(self.m_nbActive == 0)
        self.item(7).setHidden(self.m_nbInactive == 0)
        self.item(8).setHidden(self.m_nbStalled == 0)
        self.item(9).setHidden(self.m_nbStalledUploading == 0)
        self.item(10).setHidden(self.m_nbStalledDownloading == 0)
        self.item(11).setHidden(self.m_nbChecking == 0)
        self.item(12).setHidden(self.m_nbMoving == 0)
        self.item(13).setHidden(self.m_nbErrored == 0)
        """
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

        # menu.addAction(
        #     UIThemeManager.instance().getIcon("torrent-start", "media-playback-start"),
        #     self.tr("Start torrents"),
        #     self.transfer_list.startVisibleTorrents
        # )
        # menu.addAction(
        #     UIThemeManager.instance().getIcon("torrent-stop", "media-playback-pause"),
        #     self.tr("Stop torrents"),
        #     self.transfer_list.stopVisibleTorrents
        # )
        # menu.addAction(
        #     UIThemeManager.instance().getIcon("list-remove"),
        #     self.tr("Remove torrents"),
        #     self.transfer_list.deleteVisibleTorrents
        # )

        menu.popup(QCursor.pos())

    def applyFilter(self, row):
        if self.transfer_list:
            # self.transfer_list.applyStatusFilter(row)
            pass
        self.filterChanged.emit(row)

    def handleTorrentsLoaded(self, torrents):
        self.update(torrents)

    def torrentAboutToBeDeleted(self, torrent):
        if torrent in self.m_torrentsStatus:
            status = self.m_torrentsStatus.pop(torrent)

            # Decrement counters based on the status set
            r"""
            if "Downloading" in status:
                self.m_nbDownloading -= 1
            if "Seeding" in status:
                self.m_nbSeeding -= 1
            if "Completed" in status:
                self.m_nbCompleted -= 1
            if "Running" in status:
                self.m_nbRunning -= 1
            if "Stopped" in status:
                self.m_nbStopped -= 1
            if "Active" in status:
                self.m_nbActive -= 1
            if "Inactive" in status:
                self.m_nbInactive -= 1
            if "StalledUploading" in status:
                self.m_nbStalledUploading -= 1
            if "StalledDownloading" in status:
                self.m_nbStalledDownloading -= 1
            if "Checking" in status:
                self.m_nbChecking -= 1
            if "Moving" in status:
                self.m_nbMoving -= 1
            if "Errored" in status:
                self.m_nbErrored -= 1
            """
            if "Active" in status:
                self.m_nbActive -= 1
            if "Paused" in status:
                self.m_nbPaused -= 1

            self.m_nbStalled = self.m_nbStalledUploading + self.m_nbStalledDownloading

            self.updateTexts()

            # if Preferences.instance().getHideZeroStatusFilters():
            #     self.hideZeroItems()
            #     self.updateGeometry()

    def configure(self):
        # if Preferences.instance().getHideZeroStatusFilters():
        #     self.hideZeroItems()
        # else:
        for i in range(self.count()):
            self.item(i).setHidden(False)

        self.updateGeometry()

    def __del__(self):
        # Save current selection
        # Preferences.instance().setTransSelFilter(self.currentRow())
        pass
