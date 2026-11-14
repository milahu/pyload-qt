from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QLabel,
)
from PySide6.QtGui import (
    QPainter,
)


# alternative: class RotateLabel(QLabel)
r"""
# FIXME this creates a black box
from PySide6.QtWidgets import (
    QGraphicsScene,
    QGraphicsProxyWidget,
    QGraphicsView,
)
_label = QLabel(label)
font_weight = QFont.Bold if bold else QFont.Normal
font = QFont("Arial", size, font_weight)
_label.setFont(font)
# https://stackoverflow.com/search?q=%5Bpyside%5D+QGraphicsProxyWidget
# _label.setFixedSize(100, 40)
# https://www.qtcentre.org/threads/56742-how-to-make-transparent-qgraphicsproxywidget
# _label.setStyleSheet("background-color:transparent")
# _label.setAutoFillBackground(False)
# https://stackoverflow.com/a/11676527/10440128
scene = QGraphicsScene()
proxy = QGraphicsProxyWidget()
proxy.setWidget(_label)
scene.addItem(proxy)
# proxy.setPos(50, 50)
proxy.setRotation(rotate)
view = QGraphicsView(scene)
# view.setStyleSheet("background-color:transparent")
# view.setAutoFillBackground(False)
# https://stackoverflow.com/questions/60730190
_label.update()
_label.show()
view.show()
_label = view
"""


class RotateLabel(QLabel):
    # https://stackoverflow.com/a/70480783/10440128
    def __init__(self, *a, rotate=0, translate=(0, 0), **k):
        super().__init__(*a, **k)
        self.rotate = rotate
        self.translate = translate
    def paintEvent(self, e): # e: QPaintEvent
        painter = QPainter(self)
        painter.translate(self.rect().center())
        painter.rotate(self.rotate)
        painter.translate(-self.rect().center())
        if self.translate != (0, 0):
            painter.translate(*self.translate)
        painter.drawText(self.rect(), Qt.AlignHCenter | Qt.AlignVCenter, self.text())
        # QWidget.paintEvent(e)
