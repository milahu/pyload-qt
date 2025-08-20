# based on
# https://github.com/qbittorrent/qBittorrent/blob/master/src/gui/transferlistfilterswidget.cpp

from PySide6.QtWidgets import (
    QCheckBox,
    QWidget,
    QVBoxLayout,
    QScrollArea,
    QStyleOptionViewItem,
    QStyleOptionButton,
    QFrame,
    QStyle,
)
from PySide6.QtGui import (
    QPainter,
    QPalette,
    QFont,
)
from PySide6.QtCore import (
    Qt,
)
from typing import Optional
from .statusfilterwidget import StatusFilterWidget

class ArrowCheckBox(QCheckBox):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)

    def paintEvent(self, event):
        painter = QPainter(self)

        indicatorOption = QStyleOptionViewItem()
        indicatorOption.initFrom(self)
        indicatorOption.rect = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxIndicator, indicatorOption, self
        )
        if self.isChecked():
            indicatorOption.state |= QStyle.StateFlag.State_Open
        indicatorOption.state |= QStyle.StateFlag.State_Children
        self.style().drawPrimitive(
            QStyle.PrimitiveElement.PE_IndicatorBranch, indicatorOption, painter, self
        )

        labelOption = QStyleOptionButton()
        self.initStyleOption(labelOption)
        labelOption.rect = self.style().subElementRect(
            QStyle.SubElement.SE_CheckBoxContents, labelOption, self
        )
        self.style().drawControl(
            QStyle.ControlElement.CE_CheckBoxLabel, labelOption, painter, self
        )


class TransferListFiltersWidget(QWidget):
    def __init__(self, parent: Optional[QWidget], transferList, downloadFavicon: bool = False):
        super().__init__(parent)
        self.m_transferList = transferList
        self.setBackgroundRole(QPalette.ColorRole.Base)
        # pref = Preferences.instance()
        # Construct lists
        mainWidget = QWidget()
        mainWidgetLayout = QVBoxLayout(mainWidget)
        mainWidgetLayout.setContentsMargins(0, 2, 0, 0)
        mainWidgetLayout.setSpacing(2)
        mainWidgetLayout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        font = self.font()
        font.setBold(True)
        font.setCapitalization(QFont.Capitalization.AllUppercase)

        statusLabel = ArrowCheckBox(self.tr("Status"), self)
        # statusLabel.setChecked(pref.getStatusFilterState())
        statusLabel.setChecked(True)
        statusLabel.setFont(font)
        # statusLabel.toggled.connect(pref.setStatusFilterState)
        mainWidgetLayout.addWidget(statusLabel)

        statusFilters = StatusFilterWidget(self, transferList)
        # statusLabel.toggled.connect(statusFilters.toggleFilter)
        def statusLabelToggled(checked):
            if checked:
                statusFilters.show()
            else:
                statusFilters.hide()
        statusLabel.toggled.connect(statusLabelToggled)
        # statusFilters.filterChanged.connect(lambda id: print(f"statusFilters.filterChanged {id}"))
        statusFilters.filterChanged.connect(self.m_transferList.set_status_filter)
        mainWidgetLayout.addWidget(statusFilters)

        """
        categoryLabel = ArrowCheckBox(self.tr("Categories"), self)
        categoryLabel.setChecked(pref.getCategoryFilterState())
        categoryLabel.setFont(font)
        categoryLabel.toggled.connect(self.onCategoryFilterStateChanged)
        mainWidgetLayout.addWidget(categoryLabel)

        self.m_categoryFilterWidget = CategoryFilterWidget(self)
        self.m_categoryFilterWidget.actionDeleteTorrentsTriggered.connect(
            transferList.deleteVisibleTorrents
        )
        self.m_categoryFilterWidget.actionStopTorrentsTriggered.connect(
            transferList.stopVisibleTorrents
        )
        self.m_categoryFilterWidget.actionStartTorrentsTriggered.connect(
            transferList.startVisibleTorrents
        )
        self.m_categoryFilterWidget.categoryChanged.connect(
            transferList.applyCategoryFilter
        )
        self.toggleCategoryFilter(pref.getCategoryFilterState())
        mainWidgetLayout.addWidget(self.m_categoryFilterWidget)

        tagsLabel = ArrowCheckBox(self.tr("Tags"), self)
        tagsLabel.setChecked(pref.getTagFilterState())
        tagsLabel.setFont(font)
        tagsLabel.toggled.connect(self.onTagFilterStateChanged)
        mainWidgetLayout.addWidget(tagsLabel)

        self.m_tagFilterWidget = TagFilterWidget(self)
        self.m_tagFilterWidget.actionDeleteTorrentsTriggered.connect(
            transferList.deleteVisibleTorrents
        )
        self.m_tagFilterWidget.actionStopTorrentsTriggered.connect(
            transferList.stopVisibleTorrents
        )
        self.m_tagFilterWidget.actionStartTorrentsTriggered.connect(
            transferList.startVisibleTorrents
        )
        self.m_tagFilterWidget.tagChanged.connect(
            transferList.applyTagFilter
        )
        self.toggleTagFilter(pref.getTagFilterState())
        mainWidgetLayout.addWidget(self.m_tagFilterWidget)

        trackerLabel = ArrowCheckBox(self.tr("Trackers"), self)
        trackerLabel.setChecked(pref.getTrackerFilterState())
        trackerLabel.setFont(font)
        trackerLabel.toggled.connect(pref.setTrackerFilterState)
        mainWidgetLayout.addWidget(trackerLabel)

        self.m_trackersFilterWidget = TrackersFilterWidget(self, transferList, downloadFavicon)
        trackerLabel.toggled.connect(self.m_trackersFilterWidget.toggleFilter)
        mainWidgetLayout.addWidget(self.m_trackersFilterWidget)
        """

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(mainWidget)

        vLayout = QVBoxLayout(self)
        vLayout.setContentsMargins(0, 0, 0, 0)
        vLayout.addWidget(scroll)

    def setDownloadTrackerFavicon(self, value: bool):
        self.m_trackersFilterWidget.setDownloadTrackerFavicon(value)

    def addTrackers(self, torrent, trackers):
        self.m_trackersFilterWidget.addTrackers(torrent, trackers)

    def removeTrackers(self, torrent, trackers):
        self.m_trackersFilterWidget.removeTrackers(torrent, trackers)

    def refreshTrackers(self, torrent):
        self.m_trackersFilterWidget.refreshTrackers(torrent)

    def trackerEntryStatusesUpdated(self, torrent, updatedTrackers):
        self.m_trackersFilterWidget.handleTrackerStatusesUpdated(torrent, updatedTrackers)

    def onCategoryFilterStateChanged(self, enabled: bool):
        self.toggleCategoryFilter(enabled)
        Preferences.instance().setCategoryFilterState(enabled)

    def toggleCategoryFilter(self, enabled: bool):
        self.m_categoryFilterWidget.setVisible(enabled)
        current_category = self.m_categoryFilterWidget.currentCategory() if enabled else ""
        self.m_transferList.applyCategoryFilter(current_category)

    def onTagFilterStateChanged(self, enabled: bool):
        self.toggleTagFilter(enabled)
        Preferences.instance().setTagFilterState(enabled)

    def toggleTagFilter(self, enabled: bool):
        self.m_tagFilterWidget.setVisible(enabled)
        current_tag = self.m_tagFilterWidget.currentTag() if enabled else None
        self.m_transferList.applyTagFilter(current_tag)
