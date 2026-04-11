#!/usr/bin/env python3

from typing import Any
from PySide6 import QtWidgets, QtCore
from PySide6.QtUiTools import QUiLoader

from .filterrangewidget import FilterRangeWidget
from .filterlistwidget import FilterListWidget
from .utils import load_json

class FilterDialog(QtCore.QObject):
    ui: Any

    def __init__(self, initFilter, parent=None):
        super().__init__()
        self.ui = QUiLoader().load("filterdialog.ui", parent)
        self.mappings = load_json("resources/data/mapping.json")
        layout = self.ui.scrollAreaWidgetContents.layout()
        self.ageRange = FilterRangeWidget("Age", 18, 99)
        self.heightRange = FilterRangeWidget("Height [cm]", 121, 242)
        self.weightRange = FilterRangeWidget("Weight [kg]", 41, 242)
        self.positionFilter = self._makeListFilter("Sexual Position", "sexualPosition")
        self.tribeFilter = self._makeListFilter("Tribes", "tribes")
        self.bodyTypeFilter = self._makeListFilter("Body Types", "bodyType")
        self.relationshipFilter = self._makeListFilter("Relationship Status", "relationshipStatus")
        self.nsfwPicsFilter = self._makeListFilter("NSFW Pictures", "acceptsNsfwPics")
        self.lookingForFilter = self._makeListFilter("Looking for", "lookingFor")
        self.meetAtFilter = self._makeListFilter("Meet at", "meetAt")
        self.healthFilter = self._makeListFilter("Sexual health", "sexualHealth")
        ofs = 3
        layout.insertWidget(ofs,   self.ageRange.ui)
        layout.insertWidget(ofs+1, self.heightRange.ui)
        layout.insertWidget(ofs+2, self.weightRange.ui)
        layout.insertWidget(ofs+3, self.positionFilter.ui)
        layout.insertWidget(ofs+4, self.tribeFilter.ui)
        layout.insertWidget(ofs+5, self.bodyTypeFilter.ui)
        layout.insertWidget(ofs+6, self.relationshipFilter.ui)
        layout.insertWidget(ofs+7, self.nsfwPicsFilter.ui)
        layout.insertWidget(ofs+8, self.lookingForFilter.ui)
        layout.insertWidget(ofs+9, self.meetAtFilter.ui)
        layout.insertWidget(ofs+10, self.healthFilter.ui)
        self.listWidgets = [self.positionFilter, self.tribeFilter, self.bodyTypeFilter, self.relationshipFilter,
                            self.nsfwPicsFilter, self.lookingForFilter, self.meetAtFilter, self.healthFilter]
        self.listCategories = ["sexualPositions", "tribes", "bodyTypes", "relationshipStatuses",
                               "nsfwPics", "lookingFor", "meetAt", "sexualHealth"]
        self.filter = initFilter
        self.setupConnections()
        print("initFilter:", initFilter)
        self.init(initFilter)

    def setupConnections(self):
        self.ui.buttonBox.accepted.connect(self.onOkClicked)

    def _makeListFilter(self, categoryName, category):
        filterValues = list(self.mappings[category].keys())
        filterTexts = list(self.mappings[category].values())
        filterValues.append(-1)
        filterTexts.append("Not specified")
        return FilterListWidget(categoryName, filterTexts, [int(v) for v in filterValues])

    def getFilter(self):
        return self.filter

    def setRange(self, widget, filter, name, conv=int):
        getAttr = lambda a: conv(filter[a]) if a in filter else None
        enabled = filter.get(name + "FilterEnabled", False)
        widget.set(getAttr(name + "Min"), getAttr(name + "Max"), enabled)

    def setList(self, widget, filter, name):
        widget.set(filter.get(name, []), filter.get(name + "FilterEnabled", False))

    def init(self, filter):
        self.setRange(self.ageRange, filter, "age")
        self.setRange(self.heightRange, filter, "heightCm")
        self.setRange(self.weightRange, filter, "weightGrams", conv=lambda g: int(float(g) / 1000))
        for widget, name in zip(self.listWidgets, self.listCategories):
            self.setList(widget, filter, name)
        self.ui.favorites.setChecked(filter.get("favorites", False))
        self.ui.online.setChecked(filter.get("onlineOnly", False))
        self.ui.rightNow.setChecked(filter.get("rightNow", False))
        self.ui.notRecentlyChatted.setChecked(filter.get("notRecentlyChatted", False))
        self.ui.hasPictures.setChecked(filter.get("photoOnly", False))
        self.ui.hasFacePictures.setChecked(filter.get("faceOnly", False))
        self.ui.hasAlbum.setChecked(filter.get("hasAlbum", False))

    def onOkClicked(self):
        f = {}
        f["favorites"] = self.ui.favorites.isChecked()
        f["onlineOnly"] = self.ui.online.isChecked()
        f["rightNow"] = self.ui.rightNow.isChecked()
        f["notRecentlyChatted"] = self.ui.notRecentlyChatted.isChecked()
        f["photoOnly"] = self.ui.hasPictures.isChecked()
        f["faceOnly"] = self.ui.hasFacePictures.isChecked()
        f["hasAlbum"] = self.ui.hasAlbum.isChecked()
        filterByAge, minAge, maxAge = self.ageRange.get()
        f["ageFilterEnabled"] = filterByAge
        f["ageMin"] = minAge
        f["ageMax"] = maxAge
        filterByHeight, minHeight, maxHeight = self.heightRange.get()
        f["heightCmFilterEnabled"] = filterByHeight
        f["heightCmMin"] = minHeight
        f["heightCmMax"] = maxHeight
        filterByWeight, minWeight, maxWeight = self.weightRange.get()
        f["weightGramsFilterEnabled"] = filterByWeight
        f["weightGramsMin"] = minWeight * 1000
        f["weightGramsMax"] = maxWeight * 1000
        def fromList(widget, name):
            filterBy, values = widget.get()
            f[name + "FilterEnabled"] = filterBy
            f[name] = values
        for widget, name in zip(self.listWidgets, self.listCategories):
            filterBy, values = widget.get()
            f[name + "FilterEnabled"] = filterBy
            f[name] = values
        self.filter = f


def showFilterDialog(initFilter, parent):
    dlg = FilterDialog(initFilter, parent)
    if dlg.ui.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        return dlg.getFilter()
    return None
