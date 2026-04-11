#!/usr/bin/env python3
# Adapted from https://github.com/oclero/qlementine, © Olivier Cléro, MIT

import sys

from PySide6 import QtWidgets, QtGui, QtCore

class NotificationBadge(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = ""
        self.foregroundColor = QtGui.QColor(QtGui.Qt.white)
        self.backgroundColor = QtGui.QColor(QtGui.Qt.red)
        self.padding = QtCore.QMargins(0, 0, 0, 0)
        self.widget = None
        self.widgetParent = None
        self.relativePos = QtCore.QPoint(4, -4)
        self.setFocusPolicy(QtGui.Qt.NoFocus)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.setAttribute(QtGui.Qt.WA_TransparentForMouseEvents)

    def setText(self, text):
        self.text = text
        self.updateGeometry()

    def minimumSizeHint(self):
        style = self.style()
        defaultIconExtent = style.pixelMetric(QtWidgets.QStyle.PM_ButtonIconSize) if style else 16
        defaultExtent = defaultIconExtent // 2
        if not self.text:
            return QtCore.QSize(defaultExtent, defaultExtent)
        font = self.font()
        fm = QtGui.QFontMetrics(font)
        textSize = fm.boundingRect(self.text)
        h = textSize.height() + self.padding.top() + self.padding.bottom()
        w = max(h, textSize.width() + self.padding.left() + self.padding.right())
        return QtCore.QSize(w, h)

    def sizeHint(self):
        return self.minimumSizeHint()

    def paintEvent(self, pe):
        p = QtGui.QPainter(self)

        # background
        rect = self.rect()
        defaultRadius = 8
        radius = min(defaultRadius, rect.height(), rect.width())
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        p.setBrush(self.backgroundColor)
        p.setPen(QtGui.Qt.NoPen)
        p.drawRoundedRect(rect, radius, radius)

        # text
        if not self.text:
            return
        font = self.font()
        p.setFont(font)
        p.setPen(self.foregroundColor)
        p.drawText(rect, self.text, QtGui.QTextOption(QtCore.Qt.Alignment.AlignCenter))
