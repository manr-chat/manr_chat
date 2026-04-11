#!/usr/bin/env python3

from PySide6 import QtWidgets, QtCore
from PySide6.QtUiTools import QUiLoader

class FilterRangeWidget(QtCore.QObject):
    def __init__(self, name, minRange, maxRange, parent=None):
        super().__init__()
        self.ui = QUiLoader().load("filterrangewidget.ui", parent)
        self.ui.groupBox.setTitle(name + ":")
        self.ui.minValue.setRange(minRange, maxRange)
        self.ui.maxValue.setRange(minRange, maxRange)
        self.ui.minValueSlider.setRange(minRange, maxRange)
        self.ui.maxValueSlider.setRange(minRange, maxRange)
        self.setupConnections()
        self.ui.minValue.setValue(minRange)
        self.ui.maxValue.setValue(maxRange)

    def setupConnections(self):
        self.ui.minValue.valueChanged.connect(self.on_minValue_valueChanged)
        self.ui.maxValue.valueChanged.connect(self.on_maxValue_valueChanged)

    def set(self, minV, maxV, enabled):
        if minV:
            self.ui.minValue.setValue(int(minV))
        if maxV:
            self.ui.maxValue.setValue(int(maxV))
        self.ui.groupBox.setChecked(enabled)

    def getRange(self):
        minV = self.ui.minValue.value()
        maxV = self.ui.maxValue.value()
        return minV, maxV

    def isEnabled(self):
        return self.ui.groupBox.isChecked()

    def get(self):
       return self.isEnabled(), *self.getRange()

    def on_minValue_valueChanged(self, value):
       if value > self.ui.maxValue.value():
        self.ui.maxValue.setValue(value)

    def on_maxValue_valueChanged(self, value):
       if value < self.ui.minValue.value():
        self.ui.minValue.setValue(value)
