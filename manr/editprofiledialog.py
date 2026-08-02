#!/usr/bin/env python3

from typing import Any
from PySide6 import QtWidgets, QtCore, QtGui
from PySide6.QtUiTools import QUiLoader

from .filterlistwidget import FilterListWidget
from .utils import loadMappings, formatTimeStampMonth
from .image_cache import get_or_download_image, MediaDescription, MediaType

class EditProfileDialog(QtCore.QObject):
    ui: Any

    def __init__(self, model, initProfile, parent=None):
        super().__init__()
        self.ui = QUiLoader().load("editprofiledialog.ui", parent)
        self.model = model
        self.profile = initProfile
        self.mappings = loadMappings()
        layout = self.ui.scrollAreaWidgetContents.layout()
        self._fillCombobox(self.ui.sexualPosition, "sexualPosition")
        self._fillCombobox(self.ui.bodyType, "bodyType")
        self._fillCombobox(self.ui.relationshipStatus, "relationshipStatus")
        self._fillCombobox(self.ui.acceptNSFW, "acceptsNsfwPics")
        self._fillCombobox(self.ui.ethnicity, "ethnicity")
        self._fillCombobox(self.ui.hivStatus, "hivStatus")
        self.genderList = self._makeList("Gender", "genders")
        self.pronounList = self._makeList("Pronouns", "pronouns")
        self.tribeList = self._makeList("Tribes", "tribes")
        self.tribesImIntoList = self._makeList("Tribes I'm into", "tribes")
        self.lookingForList = self._makeList("Looking for", "lookingFor")
        self.meetAtList = self._makeList("Meet at", "meetAt")
        self.healthList = self._makeList("Sexual health", "sexualHealth")
        self.vaccinesList = self._makeList("Vaccinated", "vaccines")
        self.listWidgets = [self.genderList, self.pronounList, self.tribeList, self.tribesImIntoList,
                            self.lookingForList, self.meetAtList, self.healthList, self.vaccinesList]
        self.listCategories = ["genders", "pronouns", "grindrTribes", "tribesImInto", "lookingFor",
                               "meetAt", "sexualHealth", "vaccines"]
        ofs = 15
        for i, w in enumerate(self.listWidgets):
            layout.addWidget(w.ui, ofs+i, 0, 1, -1)
        self._setupConnections()
        print("Initial profile:", initProfile)
        self._init(initProfile)


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

    def _getComboboxValue(self, combo):
        value = int(combo.currentData())
        if value == -1:
            value = None
        return value

    def _makeList(self, categoryName, category):
        filterValues = list(self.mappings[category].keys())
        filterTexts = list(self.mappings[category].values())
        return FilterListWidget(categoryName, filterTexts, [int(v) for v in filterValues])

    def _getProfile(self):
        p = {}
        ip = self.profile
        p["profileId"] = ip["profileId"]
        p["displayName"] = self.ui.displayName.text()
        p["aboutMe"] = self.ui.aboutMe.toPlainText()
        p["age"] = max(18, self.ui.age.value())
        p["showAge"] = self.ui.showAge.isChecked()
        p["profileTags"] = ip.get("profileTags", [])
        p["lastTestedDate"] = ip.get("lastTestedDate", None)
        p["socialNetworks"] = ip.get("socialNetworks", {})
        p["profileImageMediaHash"] = ip.get("profileImageMediaHash", None)
        p["medias"] = ip.get("medias", [])
        p["showDistance"] = self.ui.showDistance.isChecked()
        p["approximateDistance"] = ip.get("approximateDistance", False)
        p["height"] = None
        p["weight"] = None
        if self.ui.showHeight.isChecked():
            p["height"] = self.ui.heightCm.value()
        if self.ui.showWeight.isChecked():
            p["weight"] = self.ui.weightKg.value() * 1000
        p["sexualPosition"] = self._getComboboxValue(self.ui.sexualPosition)
        p["bodyType"] = self._getComboboxValue(self.ui.bodyType)
        p["ethnicity"] = self._getComboboxValue(self.ui.ethnicity)
        p["relationshipStatus"] = self._getComboboxValue(self.ui.relationshipStatus)
        p["nsfw"] = self._getComboboxValue(self.ui.acceptNSFW)
        p["hivStatus"] = self._getComboboxValue(self.ui.hivStatus)
        for widget, name in zip(self.listWidgets, self.listCategories):
            p[name] = widget.getValues()
        # Infer these from whether they're set
        p["showTribes"] = bool(p["grindrTribes"])
        p["showPosition"] = p["sexualPosition"] is not None
        return p

    def _setList(self, widget, profile, name):
        keys = profile.get(name, [])
        checked = len(keys) > 0
        widget.set(keys, checked)

    def _init(self, profile):
        self.ui.profileId.setText(profile["profileId"])
        self.ui.displayName.setText(profile.get("displayName", ""))
        self.ui.aboutMe.setPlainText(profile.get("aboutMe", ""))
        self.ui.showDistance.setChecked(profile.get("showDistance", False))
        self.ui.showAge.setChecked(profile.get("showAge", False))
        self.ui.age.setValue(profile.get("age", None) or 0)
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
        # Read-only
        lastTested = profile.get("lastTestedDate", None)
        if lastTested:
            self.ui.lastTestedDate.setText(formatTimeStampMonth(lastTested))
        socials = profile.get("socialNetworks", {})
        if socials:
            items = [f"{network}: {user["userId"]}" for network, user in socials.items()]
            self.ui.socialNetworks.setText(", ".join(items))
        tags = profile.get("profileTags", [])
        if not tags:
            tags = profile.get("hashtags", [])
        if tags:
            self.ui.tags.setText(", ".join(tags))
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

    def _trySetProfile(self):
        p = self._getProfile()
        print("New profile:", p)
        response = self.model.setMyProfile(p)
        # TODO: error handling
        return True

    def onOkClicked(self):
        success = self._trySetProfile()
        title = self.ui.parent().windowTitle()
        if success:
            #QtWidgets.QMessageBox.information(self.ui, title, "Profile information successfully updated")
            self.ui.accept()
        else:
            QtWidgets.QMessageBox.warning(self.ui, title, "Profile information could not be updated!\n\n"+
                                          "This could be due to a network problem or because the server rejected the update due to moderation policies.")


def showEditProfileDialog(model, initProfile, parent):
    dlg = EditProfileDialog(model, initProfile, parent)
    if dlg.ui.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        # TODO: implement setting profile
        pass
