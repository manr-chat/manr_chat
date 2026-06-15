#!/usr/bin/env python3

from typing import Any

from PySide6 import QtCore, QtGui
from PySide6.QtUiTools import QUiLoader

from .appinfo import manr_email_address, display_version_str

class AboutDialog(QtCore.QObject):
    ui: Any

    def __init__(self, parent=None):
        super().__init__()
        self.ui = QUiLoader().load("aboutdialog.ui", parent)
        email = manr_email_address()
        self.ui.labelVersion.setText(display_version_str())
        self.ui.labelEmail.setText(f'<a href="{email}">{email}</a>')
        dpr = self.ui.devicePixelRatio()
        if dpr > 1.5:
            pm = QtGui.QPixmap("resources/img/icon_128.png")
            pm.setDevicePixelRatio(2.0)
            self.ui.labelIcon.setPixmap(pm)

def showAboutDialog(parent):
    dlg = AboutDialog(parent)
    dlg.ui.exec()
