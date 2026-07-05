#!/usr/bin/env python3

from typing import Any
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtUiTools import QUiLoader

from .filterlistwidget import FilterListWidget
from .utils import load_json
from .image_cache import get_or_download_image, MediaDescription, MediaType

class EditProfileDialog(QtCore.QObject):
    ui: Any

    def __init__(self, initProfile, parent=None):
        super().__init__()
        self.ui = QUiLoader().load("editprofiledialog.ui", parent)
        self.profile = initProfile
        self.mappings = load_json("resources/data/mapping.json")
        layout = self.ui.scrollAreaWidgetContents.layout()
        self._fillCombobox(self.ui.sexualPosition, "sexualPosition")
        self._fillCombobox(self.ui.bodyType, "bodyType")
        self._fillCombobox(self.ui.relationshipStatus, "relationshipStatus")
        self._fillCombobox(self.ui.acceptNSFW, "acceptsNsfwPics")
        self._fillCombobox(self.ui.ethnicity, "ethnicity")
        self._fillCombobox(self.ui.hivStatus, "hivStatus")
        self.tribeList = self._makeList("Tribes", "tribes")
        self.tribesImIntoList = self._makeList("Tribes I'm into", "tribes")
        self.lookingForList = self._makeList("Looking for", "lookingFor")
        self.meetAtList = self._makeList("Meet at", "meetAt")
        self.healthList = self._makeList("Sexual health", "sexualHealth")
        self.vaccinesList = self._makeList("Vaccinated", "vaccines")
        self.listWidgets = [self.tribeList, self.tribesImIntoList, self.lookingForList,
                            self.meetAtList, self.healthList, self.vaccinesList]
        self.listCategories = ["grindrTribes", "tribesImInto", "lookingFor", "meetAt",
                               "sexualHealth", "vaccines"]
        ofs = 11
        for i, w in enumerate(self.listWidgets):
            layout.addWidget(w.ui, ofs+i, 0, 1, -1)
        self._setupConnections()
        print("Initial profile:", initProfile)
        self._init(initProfile)
        # Edit is not yet implemented
        ok_button = self.ui.buttonBox.button(QtWidgets.QDialogButtonBox.StandardButton.Ok)
        ok_button.setEnabled(False)


    def _setupConnections(self):
        self.ui.buttonBox.accepted.connect(self.onOkClicked)

    def _fillCombobox(self, combo, category):
        values = [-1]
        texts = ["Don't show"]
        values += list(self.mappings[category].keys())
        texts += list(self.mappings[category].values())
        for text, val in zip(texts, values):
            combo.addItem(text, val)

    def _setComboboxValue(self, combo, value):
        if value is None:
            value = -1
        idx = combo.findData(value)
        combo.setCurrentIndex(idx)

    def _makeList(self, categoryName, category):
        filterValues = list(self.mappings[category].keys())
        filterTexts = list(self.mappings[category].values())
        return FilterListWidget(categoryName, filterTexts, [int(v) for v in filterValues])

    def getProfile(self):
        return self.profile

    def _setList(self, widget, profile, name):
        keys = profile.get(name, [])
        checked = len(keys) > 0
        widget.set(keys, checked)

    def _init(self, profile):
        self.ui.profileId.setText(profile["profileId"])
        self.ui.displayName.setText(profile.get("displayName", ""))
        self.ui.aboutMe.setPlainText(profile.get("aboutMe", ""))
        self.ui.showAge.setChecked(profile.get("showAge", False))
        self.ui.age.setValue(profile.get("age", 0))
        self.ui.showHeight.setChecked(bool(profile.get("height", None)))
        self.ui.heightCm.setValue(int(profile.get("height", None) or 0))
        self.ui.showWeight.setChecked(bool(profile.get("weight", None)))
        weight = profile.get("weight", None) or 0
        weight = int(round(weight/1000))
        self.ui.weightKg.setValue(weight)
        self._setComboboxValue(self.ui.sexualPosition, profile.get("sexualPosition", None))
        self._setComboboxValue(self.ui.bodyType, profile.get("bodyType", None))
        self._setComboboxValue(self.ui.ethnicity, profile.get("ethnicity", None))
        self._setComboboxValue(self.ui.relationshipStatus, profile.get("relationshipStatus", None))
        self._setComboboxValue(self.ui.acceptNSFW, profile.get("nsfw", None))
        self._setComboboxValue(self.ui.hivStatus, profile.get("hivStatus", None))
        for widget, name in zip(self.listWidgets, self.listCategories):
            self._setList(widget, profile, name)
        self._initProfilePicture(profile)

    def _initProfilePicture(self, profile):
        imgHash = profile.get("profileImageMediaHash", None)
        if not imgHash:
            return
        fname = get_or_download_image(MediaDescription(imgHash, MediaType.thumb))
        if fname:
            pm = QtGui.QPixmap(fname)
            if not pm.isNull():
                self.ui.labelPhoto.setPixmap(pm)

    def onOkClicked(self):
        # TODO: implement!
        pass


def showEditProfileDialog(initProfile, parent):
    dlg = EditProfileDialog(initProfile, parent)
    if dlg.ui.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        # TODO: implement setting profile
        pass
