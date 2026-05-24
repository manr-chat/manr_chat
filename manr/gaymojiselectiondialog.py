#!/usr/bin/env python3

from PySide6 import QtWidgets, QtGui, QtCore
from PySide6.QtUiTools import QUiLoader

from typing import Any
from .image_cache import DownloadWorker, MediaType, MediaDescription, get_cached_image_name, download_gaymoji_list
from .utils import profile, override_cursor, load_json

class GaymojiSelectionDialog(QtCore.QObject):
    ui: Any

    def __init__(self, model, chatId, parent=None):
        super().__init__()
        self.model = model
        self.chatId = chatId
        self.pixmaps = {}
        self.ui = QUiLoader().load("gaymojiselectiondialog.ui", parent)
        self.blankProfileImage = QtGui.QPixmap("resources/img/blank.png")
        self.loadingProfileImage = QtGui.QPixmap("resources/img/loading_blank.png")
        self._setupConnections()
        with override_cursor():
            self._initCategoryList()

    def _setupConnections(self):
        self.ui.categoryList.currentItemChanged.connect(self.on_categoryList_currentItemChanged)

    def getImageId(self):
        item = self.ui.imageList.currentItem()
        if not item:
            return
        return item.data(QtCore.Qt.ItemDataRole.UserRole)

    def startBackgroundDownload(self, mediaDesc):
        profile("I: GaymojiSelectionDialog: Starting Background download of", mediaDesc.name)
        worker = DownloadWorker(mediaDesc)
        worker.signals.finished.connect(self.downloadComplete)
        QtCore.QThreadPool.globalInstance().start(worker)

    @QtCore.Slot()
    def downloadComplete(self, imgDesc, imgFileName):
        profile("I: GaymojiSelectionDialog: Finished Background download of", imgDesc.name)
        print("imgDesc.mediaType:", imgDesc.mediaType)
        assert imgDesc.mediaType == MediaType.gaymoji
        for row in range(self.ui.imageList.count()):
            item = self.ui.imageList.item(row)
            itemImageId = item.data(QtCore.Qt.ItemDataRole.UserRole)
            if imgDesc.name == itemImageId:
                img = QtGui.QPixmap(imgFileName)
                self.pixmaps[itemImageId] = img
                item.setIcon(img)

    def getImage(self, imageId):
        img = self.blankProfileImage
        if imageId:
            media = MediaDescription(imageId, MediaType.gaymoji)
            imgFileName = get_cached_image_name(media)
            if imgFileName:
                img = QtGui.QPixmap(imgFileName)
            else:
                img = self.loadingProfileImage
                self.startBackgroundDownload(media)
        return img

    def _initCategoryList(self):
        self.imgDescription = load_json(download_gaymoji_list())
        for category in self.imgDescription["category"]:
            if category["expiredTime"] > 0:
                continue
            name = category["name"]
            item = QtWidgets.QListWidgetItem(name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, name)
            self.ui.categoryList.addItem(item)
        self.ui.categoryList.setCurrentRow(0)

    def _populateList(self, category):
        self.ui.imageList.clear()
        for i in self.imgDescription["gaymoji"]:
            imageId = "gaymoji/" + i["id"]
            imageName = i["name"]
            imageCat = i["category"]
            if imageCat != category:
                continue
            item = QtWidgets.QListWidgetItem(imageName)
            img = self.getImage(imageId)
            self.pixmaps[imageId] = img
            item.setIcon(img)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, imageId)
            self.ui.imageList.addItem(item)

    def on_categoryList_currentItemChanged(self, curItem, _prev):
        if not curItem:
            return
        category = curItem.data(QtCore.Qt.ItemDataRole.UserRole)
        self._populateList(category)

def showGaymojiSelectionDialog(model, chatId, parent):
    dlg = GaymojiSelectionDialog(model, chatId, parent)
    if dlg.ui.exec() == QtWidgets.QDialog.DialogCode.Accepted:
        return dlg.getImageId()
    return None
