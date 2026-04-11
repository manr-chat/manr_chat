#!/usr/bin/env python3

from typing import Any
from PySide6 import QtCore
from PySide6.QtUiTools import QUiLoader

class DetailsSelectionWidget(QtCore.QObject):
    ui: Any

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = QUiLoader().load("detailsselectionwidget.ui")
        self.setupConnections()

    def setupConnections(self):
        pass
