#!/usr/bin/env python3

from PySide6 import QtWidgets, QtCore
from PySide6.QtUiTools import QUiLoader

class FilterListWidget(QtCore.QObject):
    def __init__(self, categoryName, filterTexts, filterValues, parent=None):
        super().__init__()
        self.ui = QUiLoader().load("filterlistwidget.ui", parent)
        self.ui.groupBox.setTitle(categoryName + ":")
        self.filterTexts = filterTexts
        self.filterValues = filterValues
        assert len(filterTexts) == len(filterValues)
        for t, v in zip(filterTexts, filterValues):
            item = QtWidgets.QListWidgetItem(t)
            item.setData(QtCore.Qt.UserRole, v)
            item.setCheckState(QtCore.Qt.Unchecked)
            self.ui.listWidget.addItem(item)
        self.setupConnections()

    def setupConnections(self):
        self.ui.groupBox.toggled.connect(self.ui.listWidget.setVisible)

    def set(self, enabledKeys, enabled):
        self.ui.groupBox.setChecked(enabled)
        for i, v in enumerate(self.filterValues):
            self.ui.listWidget.item(i).setCheckState(QtCore.Qt.Checked if v in enabledKeys else QtCore.Qt.Unchecked)

    def getValues(self):
        values = []
        for i, v in enumerate(self.filterValues):
            if self.ui.listWidget.item(i).checkState() == QtCore.Qt.Checked:
                values.append(v)
        return values

    def isEnabled(self):
        return self.ui.groupBox.isChecked()

    def get(self):
       return self.isEnabled(), self.getValues()

    def on_minValue_valueChanged(self, value):
        if value > self.ui.maxValue.value():
            self.ui.maxValue.setValue(value)

    def on_maxValue_valueChanged(self, value):
        if value < self.ui.minValue.value():
            self.ui.minValue.setValue(value)
